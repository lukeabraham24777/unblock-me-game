"""All experiments. Each `run_*` function returns a JSON-serialisable dict and
is invoked by `run_all.py`, which writes results/<name>.json.

Everything is CPU-only and seeded. Seeds control parameter init, data
shuffling, and synthetic-data generation.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.datasets import make_moons

from .activations import ACT_ORDER, HELU_HI, HELU_LO, activation_fn
from .models import MLP, SmallCNN

DEVICE = torch.device("cpu")


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)


# --------------------------------------------------------------------------
# Generic supervised training loop
# --------------------------------------------------------------------------
@dataclass
class History:
    step_loss: list[float] = field(default_factory=list)   # per optimizer step
    epoch_test_acc: list[float] = field(default_factory=list)
    epoch_test_loss: list[float] = field(default_factory=list)
    epoch_train_acc: list[float] = field(default_factory=list)
    wall_time_s: float = 0.0


@torch.no_grad()
def evaluate(model: nn.Module, loader) -> tuple[float, float]:
    model.eval()
    tot, correct, loss_sum = 0, 0, 0.0
    for x, y in loader:
        logits = model(x)
        loss_sum += F.cross_entropy(logits, y, reduction="sum").item()
        correct += (logits.argmax(1) == y).sum().item()
        tot += y.numel()
    model.train()
    return correct / tot, loss_sum / tot


def train_classifier(model: nn.Module, train_loader, test_loader, epochs: int, lr: float,
                     weight_decay: float = 0.0, log_every: int = 1) -> History:
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    hist = History()
    t0 = time.time()
    model.train()
    for _ in range(epochs):
        correct, tot = 0, 0
        for i, (x, y) in enumerate(train_loader):
            logits = model(x)
            loss = F.cross_entropy(logits, y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            if i % log_every == 0:
                hist.step_loss.append(loss.item())
            correct += (logits.argmax(1) == y).sum().item()
            tot += y.numel()
        acc, tl = evaluate(model, test_loader)
        hist.epoch_test_acc.append(acc)
        hist.epoch_test_loss.append(tl)
        hist.epoch_train_acc.append(correct / tot)
    hist.wall_time_s = time.time() - t0
    return hist


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def image_loaders(name: str, root: str, batch_size: int = 128, seed: int = 0, num_workers: int = 0):
    import torchvision
    import torchvision.transforms as T

    ds_cls = {"mnist": torchvision.datasets.MNIST, "fashion": torchvision.datasets.FashionMNIST}[name]
    mean, std = {"mnist": (0.1307, 0.3081), "fashion": (0.2860, 0.3530)}[name]
    tf = T.Compose([T.ToTensor(), T.Normalize((mean,), (std,))])
    train = ds_cls(root, train=True, download=True, transform=tf)
    test = ds_cls(root, train=False, download=True, transform=tf)
    # Materialise into tensors once: far faster than per-item transforms on CPU.
    xtr = torch.stack([train[i][0] for i in range(len(train))])
    ytr = torch.tensor([train[i][1] for i in range(len(train))])
    xte = torch.stack([test[i][0] for i in range(len(test))])
    yte = torch.tensor([test[i][1] for i in range(len(test))])
    g = torch.Generator().manual_seed(seed)
    tr_loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xtr, ytr), batch_size=batch_size,
                                            shuffle=True, generator=g, num_workers=num_workers)
    te_loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xte, yte), batch_size=1000,
                                            shuffle=False)
    return tr_loader, te_loader


_IMAGE_CACHE: dict = {}


def cached_image_tensors(name: str, root: str):
    """Load once per process; loaders are then created per seed."""
    if name not in _IMAGE_CACHE:
        tr, te = image_loaders(name, root, seed=0)
        _IMAGE_CACHE[name] = (tr.dataset.tensors, te.dataset.tensors)
    return _IMAGE_CACHE[name]


def loaders_from_cache(name: str, root: str, batch_size: int, seed: int):
    (xtr, ytr), (xte, yte) = cached_image_tensors(name, root)
    g = torch.Generator().manual_seed(seed)
    tr = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xtr, ytr), batch_size=batch_size,
                                     shuffle=True, generator=g)
    te = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xte, yte), batch_size=1000)
    return tr, te


# --------------------------------------------------------------------------
# Experiment 1: activation shape (analytic, no training)
# --------------------------------------------------------------------------
def run_activation_shape() -> dict:
    x = torch.linspace(-2.0, 2.0, 4001, requires_grad=True)
    out = {"x": x.detach().tolist()}
    for a in ACT_ORDER:
        y = activation_fn(a)(x)
        (dy,) = torch.autograd.grad(y.sum(), x)
        out[a] = {"y": y.detach().tolist(), "dy": dy.tolist()}
    # zoom on the notch
    xz = torch.linspace(0.4, 0.7, 3001)
    out["zoom_x"] = xz.tolist()
    out["zoom_helu"] = activation_fn("helu")(xz).tolist()
    return out


# --------------------------------------------------------------------------
# Experiment 2: 1-D function regression
# --------------------------------------------------------------------------
TARGETS: dict[str, Callable[[torch.Tensor], torch.Tensor]] = {
    "sin(3x)": lambda x: torch.sin(3 * x),
    "|x|": lambda x: x.abs(),
    "x^2": lambda x: x ** 2,
    "step": lambda x: (x > 0).float(),
}


def run_regression_1d(seeds=(0, 1, 2, 3, 4), steps: int = 3000, hidden: int = 64, depth: int = 2,
                      lr: float = 3e-3) -> dict:
    out: dict = {"targets": list(TARGETS), "seeds": list(seeds), "steps": steps, "results": {}, "curves": {}}
    xg = torch.linspace(-2, 2, 400).unsqueeze(1)
    for tname, tf in TARGETS.items():
        out["results"][tname] = {}
        out["curves"][tname] = {"x": xg.squeeze(1).tolist(), "y_true": tf(xg).squeeze(1).tolist()}
        for a in ACT_ORDER:
            mses, fits = [], []
            for s in seeds:
                set_seed(s)
                xtr = torch.rand(512, 1) * 4 - 2
                ytr = tf(xtr) + 0.05 * torch.randn_like(xtr)
                xte = torch.rand(2000, 1) * 4 - 2
                yte = tf(xte)
                model = MLP(1, hidden, 1, depth, a)
                opt = torch.optim.Adam(model.parameters(), lr=lr)
                for _ in range(steps):
                    loss = F.mse_loss(model(xtr), ytr)
                    opt.zero_grad(set_to_none=True)
                    loss.backward()
                    opt.step()
                with torch.no_grad():
                    mses.append(F.mse_loss(model(xte), yte).item())
                    fits.append(model(xg).squeeze(1).tolist())
            out["results"][tname][a] = mses
            out["curves"][tname][a] = fits[0]   # seed-0 fit for plotting
    return out


# --------------------------------------------------------------------------
# Experiment 3: 2-D classification (moons / spirals)
# --------------------------------------------------------------------------
def make_spirals(n: int, noise: float, rng: np.random.Generator):
    n2 = n // 2
    t = np.sqrt(rng.random(n2)) * 3 * np.pi
    x1 = np.stack([t * np.cos(t), t * np.sin(t)], 1) + rng.normal(0, noise, (n2, 2))
    x2 = np.stack([-t * np.cos(t), -t * np.sin(t)], 1) + rng.normal(0, noise, (n2, 2))
    X = np.concatenate([x1, x2]) / (3 * np.pi)
    y = np.concatenate([np.zeros(n2), np.ones(n2)])
    return X.astype(np.float32), y.astype(np.int64)


def make_2d(name: str, n: int, seed: int):
    rng = np.random.default_rng(seed)
    if name == "moons":
        X, y = make_moons(n, noise=0.15, random_state=seed)
        return X.astype(np.float32), y.astype(np.int64)
    if name == "spirals":
        return make_spirals(n, 0.4, rng)
    raise ValueError(name)


def run_classification_2d(seeds=(0, 1, 2, 3, 4), steps: int = 3000, hidden: int = 64, depth: int = 2,
                          lr: float = 3e-3, grid_n: int = 200) -> dict:
    out: dict = {"datasets": ["moons", "spirals"], "seeds": list(seeds), "results": {}, "boundaries": {}}
    for dname in out["datasets"]:
        out["results"][dname] = {}
        out["boundaries"][dname] = {}
        for a in ACT_ORDER:
            accs = []
            for s in seeds:
                set_seed(s)
                Xtr, ytr = make_2d(dname, 600, s)
                Xte, yte = make_2d(dname, 4000, 1000 + s)
                Xtr_t, ytr_t = torch.from_numpy(Xtr), torch.from_numpy(ytr)
                model = MLP(2, hidden, 2, depth, a)
                opt = torch.optim.Adam(model.parameters(), lr=lr)
                for _ in range(steps):
                    loss = F.cross_entropy(model(Xtr_t), ytr_t)
                    opt.zero_grad(set_to_none=True)
                    loss.backward()
                    opt.step()
                with torch.no_grad():
                    pred = model(torch.from_numpy(Xte)).argmax(1).numpy()
                accs.append(float((pred == yte).mean()))
                if s == seeds[0]:
                    lo, hi = Xtr.min(0) - 0.3, Xtr.max(0) + 0.3
                    gx, gy = np.meshgrid(np.linspace(lo[0], hi[0], grid_n), np.linspace(lo[1], hi[1], grid_n))
                    grid = torch.from_numpy(np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float32))
                    with torch.no_grad():
                        p = F.softmax(model(grid), 1)[:, 1].numpy().reshape(grid_n, grid_n)
                    out["boundaries"][dname][a] = {
                        "extent": [float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1])],
                        "p": p.round(4).tolist(),
                    }
                    out["boundaries"][dname]["X"] = Xtr.tolist()
                    out["boundaries"][dname]["y"] = ytr.tolist()
            out["results"][dname][a] = accs
    return out


# --------------------------------------------------------------------------
# Experiment 4: image classification (MNIST / Fashion-MNIST; MLP & CNN)
# --------------------------------------------------------------------------
def run_image(dataset: str, arch: str, root: str, seeds=(0, 1, 2), epochs: int = 5, lr: float = 1e-3,
              batch_size: int = 128, hidden: int = 256, depth: int = 2) -> dict:
    out: dict = {"dataset": dataset, "arch": arch, "seeds": list(seeds), "epochs": epochs, "lr": lr,
                 "batch_size": batch_size, "hidden": hidden, "depth": depth, "runs": {}}
    for a in ACT_ORDER:
        out["runs"][a] = []
        for s in seeds:
            set_seed(s)
            tr, te = loaders_from_cache(dataset, root, batch_size, s)
            model = MLP(28 * 28, hidden, 10, depth, a) if arch == "mlp" else SmallCNN(a)
            hist = train_classifier(model, tr, te, epochs, lr, log_every=10)
            out["runs"][a].append(hist.__dict__)
            print(f"  [{dataset}/{arch}] {a:8s} seed={s} test_acc={hist.epoch_test_acc[-1]:.4f} "
                  f"({hist.wall_time_s:.0f}s)", flush=True)
    return out


# --------------------------------------------------------------------------
# Experiment 5: depth sweep (does HeLU benefit from depth like a non-linearity?)
# --------------------------------------------------------------------------
def run_depth_sweep(root: str, dataset: str = "fashion", depths=(1, 2, 4, 8), seeds=(0, 1, 2),
                    epochs: int = 3, hidden: int = 128, lr: float = 1e-3) -> dict:
    out: dict = {"dataset": dataset, "depths": list(depths), "seeds": list(seeds), "epochs": epochs, "results": {}}
    for d in depths:
        out["results"][str(d)] = {}
        for a in ACT_ORDER:
            accs = []
            for s in seeds:
                set_seed(s)
                tr, te = loaders_from_cache(dataset, root, 128, s)
                model = MLP(28 * 28, hidden, 10, d, a)
                hist = train_classifier(model, tr, te, epochs, lr, log_every=10**9)
                accs.append(hist.epoch_test_acc[-1])
            out["results"][str(d)][a] = accs
            print(f"  [depth={d}] {a:8s} acc={np.mean(accs):.4f}±{np.std(accs):.4f}", flush=True)
    return out


# --------------------------------------------------------------------------
# Experiment 6: notch occupancy + effective linearity of trained HeLU nets
# --------------------------------------------------------------------------
@torch.no_grad()
def notch_stats(model: MLP, x: torch.Tensor) -> list[float]:
    """Fraction of pre-activations in [0.5, 0.6] per hidden layer."""
    return [float(((h >= HELU_LO) & (h <= HELU_HI)).float().mean()) for h in model.pre_activations(x)]


@torch.no_grad()
def linear_fit_r2(model: nn.Module, x: torch.Tensor) -> float:
    """R^2 of the best least-squares *linear* map x -> model(x). 1.0 == exactly linear."""
    X = x.flatten(1).double()
    Y = model(x).double()
    Xa = torch.cat([X, torch.ones(X.shape[0], 1, dtype=X.dtype)], 1)
    W = torch.linalg.lstsq(Xa, Y).solution
    resid = ((Xa @ W - Y) ** 2).sum()
    tot = ((Y - Y.mean(0)) ** 2).sum()
    return float(1 - resid / tot)


def run_linearity(root: str, dataset: str = "fashion", seeds=(0, 1, 2), epochs: int = 3, hidden: int = 256,
                  depth: int = 2, lr: float = 1e-3) -> dict:
    out: dict = {"dataset": dataset, "seeds": list(seeds), "epochs": epochs, "results": {}}
    (xtr, ytr), (xte, yte) = cached_image_tensors(dataset, root)
    probe = xte[:2000]
    for a in ACT_ORDER:
        recs = []
        for s in seeds:
            set_seed(s)
            tr, te = loaders_from_cache(dataset, root, 128, s)
            model = MLP(28 * 28, hidden, 10, depth, a)
            init_notch = notch_stats(model, probe)
            init_r2 = linear_fit_r2(model, probe)
            hist = train_classifier(model, tr, te, epochs, lr, log_every=10**9)
            recs.append({
                "test_acc": hist.epoch_test_acc[-1],
                "notch_frac_init": init_notch,
                "notch_frac_trained": notch_stats(model, probe),
                "linear_r2_init": init_r2,
                "linear_r2_trained": linear_fit_r2(model, probe),
            })
            print(f"  [linearity] {a:8s} seed={s} acc={recs[-1]['test_acc']:.4f} "
                  f"R2={recs[-1]['linear_r2_trained']:.4f} notch={recs[-1]['notch_frac_trained']}", flush=True)
        out["results"][a] = recs
    return out


# --------------------------------------------------------------------------
# Experiment 7: micro-benchmark of the activation itself
# --------------------------------------------------------------------------
def run_microbench(n: int = 4_000_000, reps: int = 20) -> dict:
    x = torch.randn(n, requires_grad=True)
    out = {"n": n, "reps": reps, "results": {}}
    for a in ACT_ORDER:
        f = activation_fn(a)
        for _ in range(3):  # warm-up
            y = f(x); y.sum().backward(); x.grad = None
        ts = []
        for _ in range(reps):
            t0 = time.perf_counter()
            y = f(x)
            y.sum().backward()
            x.grad = None
            ts.append(time.perf_counter() - t0)
        out["results"][a] = {"mean_ms": 1e3 * float(np.mean(ts)), "std_ms": 1e3 * float(np.std(ts))}
    return out


# --------------------------------------------------------------------------
# Experiment 9: HeLU variants (notch position / depth / width ablation)
# --------------------------------------------------------------------------
def _train_reg1d_one(act: str, target: str, seed: int, steps: int, hidden: int, depth: int, lr: float) -> float:
    set_seed(seed)
    tf = TARGETS[target]
    xtr = torch.rand(512, 1) * 4 - 2
    ytr = tf(xtr) + 0.05 * torch.randn_like(xtr)
    xte = torch.rand(2000, 1) * 4 - 2
    model = MLP(1, hidden, 1, depth, act)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for _ in range(steps):
        loss = F.mse_loss(model(xtr), ytr)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    with torch.no_grad():
        return F.mse_loss(model(xte), tf(xte)).item()


def _train_cls2d_one(act: str, dname: str, seed: int, steps: int, hidden: int, depth: int, lr: float) -> float:
    set_seed(seed)
    Xtr, ytr = make_2d(dname, 600, seed)
    Xte, yte = make_2d(dname, 4000, 1000 + seed)
    Xtr_t, ytr_t = torch.from_numpy(Xtr), torch.from_numpy(ytr)
    model = MLP(2, hidden, 2, depth, act)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for _ in range(steps):
        loss = F.cross_entropy(model(Xtr_t), ytr_t)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    with torch.no_grad():
        pred = model(torch.from_numpy(Xte)).argmax(1).numpy()
    return float((pred == yte).mean())


def run_variants(root: str, variants: list[str] | None = None, seeds=(0, 1, 2), steps: int = 3000,
                 epochs: int = 3, hidden: int = 64, depth: int = 2, lr: float = 3e-3,
                 image_hidden: int = 256, image_lr: float = 1e-3) -> dict:
    """Same protocols as E2 / E3 / E4 (Fashion-MNIST MLP) for every HeLU variant."""
    from .activations import HELU_VARIANTS

    variants = variants or list(HELU_VARIANTS)
    out: dict = {"variants": variants, "params": {v: HELU_VARIANTS[v] for v in variants}, "seeds": list(seeds),
                 "reg_targets": ["sin(3x)", "x^2"], "cls_datasets": ["moons", "spirals"], "epochs": epochs,
                 "results": {}}
    for v in variants:
        r: dict = {"reg1d": {}, "cls2d": {}, "fashion_mlp": []}
        for t in out["reg_targets"]:
            r["reg1d"][t] = [_train_reg1d_one(v, t, s, steps, hidden, depth, lr) for s in seeds]
        for dname in out["cls_datasets"]:
            r["cls2d"][dname] = [_train_cls2d_one(v, dname, s, steps, hidden, depth, lr) for s in seeds]
        for s in seeds:
            set_seed(s)
            tr, te = loaders_from_cache("fashion", root, 128, s)
            model = MLP(28 * 28, image_hidden, 10, 2, v)
            hist = train_classifier(model, tr, te, epochs, image_lr, log_every=10**9)
            r["fashion_mlp"].append(hist.epoch_test_acc[-1])
        out["results"][v] = r
        print(f"  [variant {v:18s}] sin MSE={np.mean(r['reg1d']['sin(3x)']):.4f} "
              f"x^2 MSE={np.mean(r['reg1d']['x^2']):.4f} moons={np.mean(r['cls2d']['moons']):.4f} "
              f"spirals={np.mean(r['cls2d']['spirals']):.4f} fashion={np.mean(r['fashion_mlp']):.4f}", flush=True)
    return out
