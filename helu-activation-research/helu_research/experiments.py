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
              batch_size: int = 128, hidden: int = 256, depth: int = 2, acts=ACT_ORDER) -> dict:
    out: dict = {"dataset": dataset, "arch": arch, "seeds": list(seeds), "epochs": epochs, "lr": lr,
                 "batch_size": batch_size, "hidden": hidden, "depth": depth, "acts": list(acts), "runs": {}}
    for a in acts:
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
                    epochs: int = 3, hidden: int = 128, lr: float = 1e-3, acts=ACT_ORDER) -> dict:
    out: dict = {"dataset": dataset, "depths": list(depths), "seeds": list(seeds), "epochs": epochs,
                 "acts": list(acts), "results": {}}
    for d in depths:
        out["results"][str(d)] = {}
        for a in acts:
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
def notch_stats(model: MLP, x: torch.Tensor, lo: float = HELU_LO, hi: float = HELU_HI) -> list[float]:
    """Fraction of pre-activations in [lo, hi] per hidden layer."""
    return [float(((h >= lo) & (h <= hi)).float().mean()) for h in model.pre_activations(x)]


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


# --------------------------------------------------------------------------
# Experiment 10: band occupancy / linearity for selected notch variants (Fashion-MNIST MLP)
# --------------------------------------------------------------------------
def run_variant_occupancy(root: str, variants=("n0.5-0.6_s0.9", "n0.5-1.0_s0.2", "n0.5-2.0_s0.2", "n0.5-inf_s0.2",
                                               "n-0.68-0.68_s0.5"),
                          seeds=(0, 1, 2), epochs: int = 3, hidden: int = 256, depth: int = 2,
                          lr: float = 1e-3) -> dict:
    from .activations import HELU_VARIANTS

    out: dict = {"variants": list(variants), "seeds": list(seeds), "epochs": epochs, "results": {}}
    (xtr, ytr), (xte, yte) = cached_image_tensors("fashion", root)
    probe = xte[:2000]
    for v in variants:
        lo, hi, _ = HELU_VARIANTS[v]
        recs = []
        for s in seeds:
            set_seed(s)
            tr, te = loaders_from_cache("fashion", root, 128, s)
            model = MLP(28 * 28, hidden, 10, depth, v)
            init_band, init_r2 = notch_stats(model, probe, lo, hi), linear_fit_r2(model, probe)
            hist = train_classifier(model, tr, te, epochs, lr, log_every=10**9)
            recs.append({"test_acc": hist.epoch_test_acc[-1], "band_frac_init": init_band,
                         "band_frac_trained": notch_stats(model, probe, lo, hi),
                         "linear_r2_init": init_r2, "linear_r2_trained": linear_fit_r2(model, probe)})
            print(f"  [occupancy {v:14s}] seed={s} acc={recs[-1]['test_acc']:.4f} "
                  f"band init={[round(b, 3) for b in init_band]} trained={[round(b, 3) for b in recs[-1]['band_frac_trained']]} "
                  f"R2={recs[-1]['linear_r2_trained']:.4f}", flush=True)
        out["results"][v] = recs
    return out


# --------------------------------------------------------------------------
# Experiment 11: extra activations (currently the sawtooth y = x/2 - floor(x/2))
# --------------------------------------------------------------------------
def run_extra(root: str, names=("sawtooth",), seeds=(0, 1, 2), steps: int = 3000, epochs: int = 3,
              hidden: int = 64, depth: int = 2, lr: float = 3e-3, image_hidden: int = 256,
              image_lr: float = 1e-3, grid_n: int = 200) -> dict:
    """Same protocols as E9 (sin 3x, x^2, moons, spirals, Fashion-MNIST MLP) plus stored seed-0 fits,
    decision boundaries, linear-fit R^2 and the gradient norm reaching the first hidden layer."""
    out: dict = {"names": list(names), "seeds": list(seeds), "epochs": epochs,
                 "reg_targets": ["sin(3x)", "x^2"], "cls_datasets": ["moons", "spirals"], "results": {},
                 "curves": {}, "boundaries": {}}
    xg = torch.linspace(-2, 2, 400).unsqueeze(1)
    x_shape = torch.linspace(-5, 5, 2001)
    out["shape"] = {nm: activation_fn(nm)(x_shape).tolist() for nm in names}
    out["shape"]["x"] = x_shape.tolist()
    (xtr_img, _), (xte_img, _) = cached_image_tensors("fashion", root)
    probe = xte_img[:2000]
    for nm in names:
        r: dict = {"reg1d": {}, "cls2d": {}, "fashion_mlp": [], "fashion_r2": [], "fashion_grad_norm_l1": []}
        out["curves"][nm], out["boundaries"][nm] = {}, {}
        for t in out["reg_targets"]:
            mses = []
            for s in seeds:
                set_seed(s)
                tf = TARGETS[t]
                xtr = torch.rand(512, 1) * 4 - 2
                ytr = tf(xtr) + 0.05 * torch.randn_like(xtr)
                xte = torch.rand(2000, 1) * 4 - 2
                model = MLP(1, hidden, 1, depth, nm)
                opt = torch.optim.Adam(model.parameters(), lr=lr)
                for _ in range(steps):
                    loss = F.mse_loss(model(xtr), ytr)
                    opt.zero_grad(set_to_none=True)
                    loss.backward()
                    opt.step()
                with torch.no_grad():
                    mses.append(F.mse_loss(model(xte), tf(xte)).item())
                    if s == seeds[0]:
                        out["curves"][nm][t] = {"x": xg.squeeze(1).tolist(), "y_true": tf(xg).squeeze(1).tolist(),
                                                "fit": model(xg).squeeze(1).tolist()}
            r["reg1d"][t] = mses
        for dname in out["cls_datasets"]:
            accs = []
            for s in seeds:
                set_seed(s)
                Xtr, ytr = make_2d(dname, 600, s)
                Xte, yte = make_2d(dname, 4000, 1000 + s)
                Xtr_t, ytr_t = torch.from_numpy(Xtr), torch.from_numpy(ytr)
                model = MLP(2, hidden, 2, depth, nm)
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
                        pgrid = F.softmax(model(grid), 1)[:, 1].numpy().reshape(grid_n, grid_n)
                    out["boundaries"][nm][dname] = {"extent": [float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1])],
                                                    "p": pgrid.round(4).tolist(), "X": Xtr.tolist(), "y": ytr.tolist()}
            r["cls2d"][dname] = accs
        for s in seeds:
            set_seed(s)
            tr, te = loaders_from_cache("fashion", root, 128, s)
            model = MLP(28 * 28, image_hidden, 10, 2, nm)
            # gradient norm reaching the first hidden layer on one batch (is anything trainable?)
            xb, yb = next(iter(tr))
            F.cross_entropy(model(xb), yb).backward()
            r["fashion_grad_norm_l1"].append(float(model.net[0].weight.grad.norm()))
            model.zero_grad(set_to_none=True)
            hist = train_classifier(model, tr, te, epochs, image_lr, log_every=10**9)
            r["fashion_mlp"].append(hist.epoch_test_acc[-1])
            r["fashion_r2"].append(linear_fit_r2(model, probe))
        out["results"][nm] = r
        print(f"  [{nm:9s}] sin MSE={np.mean(r['reg1d']['sin(3x)']):.4f} x^2 MSE={np.mean(r['reg1d']['x^2']):.4f} "
              f"moons={np.mean(r['cls2d']['moons']):.4f} spirals={np.mean(r['cls2d']['spirals']):.4f} "
              f"fashion={np.mean(r['fashion_mlp']):.4f} R2={np.mean(r['fashion_r2']):.4f} "
              f"grad_l1={np.mean(r['fashion_grad_norm_l1']):.2e}", flush=True)
    return out


# --------------------------------------------------------------------------
# Experiment 12: sawtooth diagnostics: learning-rate sweep and descent-direction test
# --------------------------------------------------------------------------
def _descent_fraction(act: str, root: str, etas=(1e-3, 1e-2, 1e-1), n_batches: int = 50, seed: int = 0,
                      hidden: int = 256) -> dict:
    """For `n_batches` mini-batches at initialisation: take a plain gradient step of size eta along
    -grad and record the actual change in the batch loss. Returns the fraction of batches on which the
    loss went DOWN (i.e. the autograd gradient was a descent direction), per eta, plus the mean
    relative change."""
    set_seed(seed)
    tr, _ = loaders_from_cache("fashion", root, 128, seed)
    model = MLP(28 * 28, hidden, 10, 2, act)
    out = {}
    for eta in etas:
        down, rel = 0, []
        it = iter(tr)
        for _ in range(n_batches):
            x, y = next(it)
            params = [p for p in model.parameters()]
            loss0 = F.cross_entropy(model(x), y)
            grads = torch.autograd.grad(loss0, params)
            with torch.no_grad():
                for p_, g in zip(params, grads):
                    p_ -= eta * g
                loss1 = F.cross_entropy(model(x), y)
                for p_, g in zip(params, grads):
                    p_ += eta * g
            d = (loss1 - loss0).item()
            down += d < 0
            rel.append(d / loss0.item())
        out[str(eta)] = {"frac_decrease": down / n_batches, "mean_rel_change": float(np.mean(rel))}
    return out


def run_sawtooth_diagnostics(root: str, lrs=(1e-2, 1e-3, 1e-4, 1e-5), seeds=(0, 1, 2), steps: int = 3000,
                             epochs: int = 3, acts_for_descent=("sawtooth", "relu", "helu", "identity")) -> dict:
    out: dict = {"lrs": list(lrs), "seeds": list(seeds), "epochs": epochs, "lr_sweep": {}, "descent": {}}
    (_, _), (xte, _) = cached_image_tensors("fashion", root)
    probe = xte[:2000]
    for lr in lrs:
        r = {"moons": [], "spirals": [], "fashion_mlp": [], "preact_std_init": [], "preact_std_trained": [],
             "final_train_loss": []}
        for s in seeds:
            r["moons"].append(_train_cls2d_one("sawtooth", "moons", s, steps, 64, 2, lr))
            r["spirals"].append(_train_cls2d_one("sawtooth", "spirals", s, steps, 64, 2, lr))
            set_seed(s)
            tr, te = loaders_from_cache("fashion", root, 128, s)
            model = MLP(28 * 28, 256, 10, 2, "sawtooth")
            with torch.no_grad():
                r["preact_std_init"].append(float(model.pre_activations(probe)[0].std()))
            hist = train_classifier(model, tr, te, epochs, lr, log_every=10)
            with torch.no_grad():
                r["preact_std_trained"].append(float(model.pre_activations(probe)[0].std()))
            r["fashion_mlp"].append(hist.epoch_test_acc[-1])
            r["final_train_loss"].append(float(np.mean(hist.step_loss[-20:])))
        out["lr_sweep"][str(lr)] = r
        print(f"  [saw lr={lr:g}] moons={np.mean(r['moons']):.3f} spirals={np.mean(r['spirals']):.3f} "
              f"fashion={np.mean(r['fashion_mlp']):.4f} loss={np.mean(r['final_train_loss']):.3f} "
              f"preact std {np.mean(r['preact_std_init']):.2f} -> {np.mean(r['preact_std_trained']):.2f}", flush=True)
    for a in acts_for_descent:
        out["descent"][a] = _descent_fraction(a, root)
        print(f"  [descent {a:9s}] " + " ".join(f"eta={k}: {v['frac_decrease']:.2f}" for k, v in out["descent"][a].items()),
              flush=True)
    return out


# --------------------------------------------------------------------------
# Experiment 13: tune the slope-stepping function (W, delta) on a validation split, then head-to-head
# --------------------------------------------------------------------------
def fashion_trainval_loaders(root: str, batch_size: int, seed: int, n_val: int = 10_000):
    """Fashion-MNIST split into 50k train / 10k validation (fixed split, seed-independent)."""
    (xtr, ytr), _ = cached_image_tensors("fashion", root)
    xv, yv = xtr[-n_val:], ytr[-n_val:]
    xt, yt = xtr[:-n_val], ytr[:-n_val]
    g = torch.Generator().manual_seed(seed)
    tr = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xt, yt), batch_size=batch_size, shuffle=True,
                                     generator=g)
    va = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xv, yv), batch_size=1000)
    return tr, va


def run_stepslope_tune(root: str, widths=(0.5, 1.0, 2.0), deltas=(0.5, 1.0, 2.0, 4.0), seeds=(0, 1, 2),
                       epochs: int = 3, steps: int = 3000, hidden: int = 64, depth: int = 2, lr: float = 3e-3,
                       image_hidden: int = 256, image_lr: float = 1e-3, reference=("gelu", "relu")) -> dict:
    """Grid over (W, delta). Selection metric: Fashion-MNIST *validation* accuracy (50k/10k split of the
    training set), so the test set is untouched until the head-to-head. Toy tasks are recorded for context.
    GELU and ReLU are run under the identical validation protocol as reference points."""
    from .activations import stepslope_name

    names = [stepslope_name(w, d) for w in widths for d in deltas]
    out: dict = {"widths": list(widths), "deltas": list(deltas), "names": names, "seeds": list(seeds),
                 "epochs": epochs, "results": {}, "reference": {}}

    def one(nm: str) -> dict:
        r: dict = {"val_acc": [], "final_train_loss": [], "sin": [], "moons": [], "spirals": []}
        for s in seeds:
            set_seed(s)
            tr, va = fashion_trainval_loaders(root, 128, s)
            model = MLP(28 * 28, image_hidden, 10, 2, nm)
            hist = train_classifier(model, tr, va, epochs, image_lr, log_every=10)
            r["val_acc"].append(hist.epoch_test_acc[-1])
            r["final_train_loss"].append(float(np.mean(hist.step_loss[-20:])))
            r["sin"].append(_train_reg1d_one(nm, "sin(3x)", s, steps, hidden, depth, lr))
            r["moons"].append(_train_cls2d_one(nm, "moons", s, steps, hidden, depth, lr))
            r["spirals"].append(_train_cls2d_one(nm, "spirals", s, steps, hidden, depth, lr))
        return r

    for nm in names:
        out["results"][nm] = one(nm)
        r = out["results"][nm]
        print(f"  [tune {nm:14s}] val={np.mean(r['val_acc']):.4f}±{np.std(r['val_acc']):.4f} "
              f"loss={np.mean(r['final_train_loss']):.3f} sin={np.mean(r['sin']):.4f} "
              f"moons={np.mean(r['moons']):.3f} spirals={np.mean(r['spirals']):.3f}", flush=True)
    for a in reference:
        out["reference"][a] = one(a)
        r = out["reference"][a]
        print(f"  [ref  {a:14s}] val={np.mean(r['val_acc']):.4f}±{np.std(r['val_acc']):.4f} "
              f"sin={np.mean(r['sin']):.4f} moons={np.mean(r['moons']):.3f} spirals={np.mean(r['spirals']):.3f}",
              flush=True)
    best = max(names, key=lambda n: np.mean(out["results"][n]["val_acc"]))
    out["best"] = best
    print(f"  best by validation accuracy: {best}", flush=True)
    return out


def run_stepslope_final(root: str, best: str, acts_ref=("relu", "gelu"), mlp_seeds=(0, 1, 2, 3, 4),
                        cnn_seeds=(0, 1, 2), epochs: int = 5) -> dict:
    """Head-to-head of the tuned slope-stepper against the baselines under the E4/E5/E6 protocols."""
    acts = list(acts_ref) + [best]
    out: dict = {"best": best, "acts": acts}
    out["mnist_mlp"] = run_image("mnist", "mlp", root, seeds=mlp_seeds, epochs=epochs, acts=acts)
    out["fashion_mlp"] = run_image("fashion", "mlp", root, seeds=mlp_seeds, epochs=epochs, acts=acts)
    out["fashion_cnn"] = run_image("fashion", "cnn", root, seeds=cnn_seeds, epochs=epochs, acts=acts)
    out["depth"] = run_depth_sweep(root, seeds=(0, 1, 2), epochs=3, acts=acts)
    return out
