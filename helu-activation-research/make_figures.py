#!/usr/bin/env python3
"""Build every figure in figures/ and the auto-generated LaTeX tables in
paper/generated/ from results/*.json.  Run after run_all.py."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from helu_research.activations import ACT_LABEL, ACT_ORDER  # noqa: E402

ROOT = Path(__file__).resolve().parent
RES, FIG, GEN = ROOT / "results", ROOT / "figures", ROOT / "paper" / "generated"
FIG.mkdir(exist_ok=True)
GEN.mkdir(parents=True, exist_ok=True)

# Categorical palette (validated CVD-safe order): blue, orange, aqua; neutral gray for the control.
COLOR = {"relu": "#2a78d6", "gelu": "#eb6834", "helu": "#1baf7a", "identity": "#898781"}
STYLE = {"relu": "-", "gelu": "-", "helu": "-", "identity": "--"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9,
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": INK2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "lines.linewidth": 1.6,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "pdf.fonttype": 42,
})


def load(name: str) -> dict:
    with open(RES / f"{name}.json") as f:
        return json.load(f)


def legend_handles(acts=ACT_ORDER):
    return [Line2D([0], [0], color=COLOR[a], ls=STYLE[a], lw=1.8, label=ACT_LABEL[a]) for a in acts]


def save(fig, name: str):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=200)
    plt.close(fig)
    print("wrote", name)


def ms(v):  # mean ± std string
    v = np.asarray(v, float)
    return f"{v.mean():.4f} $\\pm$ {v.std(ddof=1) if len(v) > 1 else 0:.4f}"


def welch(a, b):
    """Welch t-test; returns (t, p). Falls back gracefully if either has n<2."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return float(t), float(p)


def pfmt(p):
    if np.isnan(p):
        return "--"
    return "$<10^{-4}$" if p < 1e-4 else f"{p:.3g}"


# ---------------------------------------------------------------- Figure 1: shape
def fig_activation():
    d = load("shape")
    x = np.array(d["x"])
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.2))
    ax = axes[0]
    for a in ["relu", "gelu", "helu"]:
        ax.plot(x, d[a]["y"], color=COLOR[a], label=ACT_LABEL[a])
    ax.set(xlabel="$x$", ylabel="$f(x)$", title="Activation", xlim=(-2, 2), ylim=(-0.5, 2))
    ax.axhline(0, color=GRID, lw=0.6, zorder=0)
    ax.axvline(0, color=GRID, lw=0.6, zorder=0)
    ax.legend(loc="upper left")

    ax = axes[1]
    xz, yz = np.array(d["zoom_x"]), np.array(d["zoom_helu"])
    # Break the line at the discontinuities so the jumps are visible.
    inside = (xz >= 0.5) & (xz <= 0.6)
    for m in (~inside & (xz < 0.5), inside, ~inside & (xz > 0.6)):
        ax.plot(xz[m], yz[m], color=COLOR["helu"])
    ax.plot(xz, xz, color=MUTED, lw=0.8, ls=":", label="$y=x$")
    for x0 in (0.5, 0.6):
        ax.plot([x0], [x0], "o", ms=4, mfc="white", mec=COLOR["helu"], mew=1.2)
        ax.plot([x0], [0.9 * x0], "o", ms=4, color=COLOR["helu"])
    ax.axvspan(0.5, 0.6, color=COLOR["helu"], alpha=0.08, lw=0)
    ax.set(xlabel="$x$", title="HeLU, zoom on the notch", xlim=(0.4, 0.7), ylim=(0.4, 0.7))
    ax.legend(loc="upper left")

    ax = axes[2]
    for a in ["relu", "gelu", "helu"]:
        ax.plot(x, d[a]["dy"], color=COLOR[a], label=ACT_LABEL[a])
    ax.set(xlabel="$x$", ylabel="$f'(x)$", title="Derivative", xlim=(-2, 2), ylim=(-0.15, 1.25))
    ax.axhline(0, color=GRID, lw=0.6, zorder=0)
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig_activation")


# ---------------------------------------------------------------- Figure 2: 1-D regression
def fig_reg1d():
    d = load("reg1d")
    targets = d["targets"]
    fig, axes = plt.subplots(1, len(targets), figsize=(7.0, 2.0), sharex=True)
    for ax, t in zip(axes, targets):
        c = d["curves"][t]
        ax.plot(c["x"], c["y_true"], color=INK, lw=1.0, ls=":", label="target")
        for a in ACT_ORDER:
            ax.plot(c["x"], c[a], color=COLOR[a], ls=STYLE[a], lw=1.4)
        ax.set_title(f"$y = {t}$" if t not in ("step",) else "$y = \\mathbf{1}[x>0]$")
        ax.set_xlim(-2, 2)
        ax.set_xlabel("$x$")
    axes[0].set_ylabel("$f(x)$")
    handles = [Line2D([0], [0], color=INK, ls=":", lw=1.0, label="target")] + legend_handles()
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout(w_pad=1.0)
    save(fig, "fig_reg1d_fits")

    # MSE dot plot (log scale), one panel per target, seeds as small dots + mean as bar.
    fig, axes = plt.subplots(1, len(targets), figsize=(7.0, 1.9))
    for ax, t in zip(axes, targets):
        for i, a in enumerate(ACT_ORDER):
            v = np.array(d["results"][t][a])
            ax.bar(i, v.mean(), color=COLOR[a], width=0.62, alpha=0.9, lw=0)
            ax.scatter(np.full(len(v), i) + np.linspace(-0.15, 0.15, len(v)), v, s=8, color=INK, zorder=3)
        ax.set_yscale("log")
        ax.set_xticks(range(len(ACT_ORDER)))
        ax.set_xticklabels(["ReLU", "GELU", "HeLU", "Lin."])
        ax.set_title(f"$y = {t}$" if t != "step" else "$y = \\mathbf{1}[x>0]$")
        ax.grid(axis="y")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("test MSE (log)")
    fig.tight_layout(w_pad=1.0)
    save(fig, "fig_reg1d_mse")


# ---------------------------------------------------------------- Figure 3: 2-D boundaries
def fig_cls2d():
    d = load("cls2d")
    dsets = d["datasets"]
    fig, axes = plt.subplots(len(dsets), 4, figsize=(7.0, 3.6))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
    for r, ds in enumerate(dsets):
        B = d["boundaries"][ds]
        X, y = np.array(B["X"]), np.array(B["y"])
        for c, a in enumerate(ACT_ORDER):
            ax = axes[r, c]
            b = B[a]
            ax.imshow(np.array(b["p"]), extent=b["extent"], origin="lower", cmap=cmap, vmin=0, vmax=1,
                      aspect="auto", interpolation="bilinear")
            ax.contour(np.linspace(b["extent"][0], b["extent"][1], len(b["p"][0])),
                       np.linspace(b["extent"][2], b["extent"][3], len(b["p"])),
                       np.array(b["p"]), levels=[0.5], colors=INK, linewidths=0.8)
            ax.scatter(X[y == 0, 0], X[y == 0, 1], s=3, color="#0d366b", lw=0)
            ax.scatter(X[y == 1, 0], X[y == 1, 1], s=3, color="#8a1f1f", lw=0)
            acc = np.mean(d["results"][ds][a])
            ax.set_title(f"{ACT_LABEL[a].split(' ')[0]}  ·  acc {acc:.3f}", fontsize=8.5)
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(True); s.set_color("#c3c2b7")
        axes[r, 0].set_ylabel(ds)
    fig.tight_layout(h_pad=0.8, w_pad=0.5)
    save(fig, "fig_cls2d")


# ---------------------------------------------------------------- Figure 4: training curves
def smooth(v, k=25):
    v = np.asarray(v, float)
    if len(v) < k:
        return v
    return np.convolve(v, np.ones(k) / k, mode="valid")


def fig_curves():
    names = [("mnist_mlp", "MNIST / MLP"), ("fashion_mlp", "Fashion-MNIST / MLP"), ("fashion_cnn", "Fashion-MNIST / CNN")]
    fig, axes = plt.subplots(2, 3, figsize=(7.0, 3.9))
    for c, (n, title) in enumerate(names):
        d = load(n)
        ax = axes[0, c]
        for a in ACT_ORDER:
            L = np.mean([smooth(r["step_loss"]) for r in d["runs"][a]], 0)
            ax.plot(np.arange(len(L)) * 10, L, color=COLOR[a], ls=STYLE[a], lw=1.3)
        ax.set_yscale("log")
        ax.set_title(title)
        ax.set_xlabel("optimizer step")
        ax.grid(axis="y")
        ax = axes[1, c]
        ep = np.arange(1, d["epochs"] + 1)
        for a in ACT_ORDER:
            A = np.array([r["epoch_test_acc"] for r in d["runs"][a]])
            ax.plot(ep, A.mean(0), color=COLOR[a], ls=STYLE[a], marker="o", ms=3.5)
            ax.fill_between(ep, A.mean(0) - A.std(0), A.mean(0) + A.std(0), color=COLOR[a], alpha=0.15, lw=0)
        ax.set_xlabel("epoch")
        ax.set_xticks(ep)
        ax.grid(axis="y")
    axes[0, 0].set_ylabel("train loss (smoothed)")
    axes[1, 0].set_ylabel("test accuracy")
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(h_pad=1.0, w_pad=1.0)
    save(fig, "fig_curves")


# ---------------------------------------------------------------- Figure 5: summary accuracy
def fig_summary():
    names = [("mnist_mlp", "MNIST\nMLP"), ("fashion_mlp", "Fashion-MNIST\nMLP"), ("fashion_cnn", "Fashion-MNIST\nCNN")]
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.1))
    for ax, (n, title) in zip(axes, names):
        d = load(n)
        for i, a in enumerate(ACT_ORDER):
            v = np.array([r["epoch_test_acc"][-1] for r in d["runs"][a]])
            ax.bar(i, v.mean(), color=COLOR[a], width=0.62, lw=0)
            ax.errorbar(i, v.mean(), yerr=v.std(ddof=1) if len(v) > 1 else 0, color=INK, capsize=2, lw=0.8)
            ax.scatter(np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v)), v, s=7, color=INK, zorder=3)
            ax.text(i, ax.get_ylim()[0], "", ha="center")
        lo = min(np.mean([r["epoch_test_acc"][-1] for r in d["runs"][a]]) for a in ACT_ORDER)
        hi = max(np.mean([r["epoch_test_acc"][-1] for r in d["runs"][a]]) for a in ACT_ORDER)
        ax.set_ylim(lo - 0.02, hi + 0.01)
        ax.set_xticks(range(4))
        ax.set_xticklabels(["ReLU", "GELU", "HeLU", "Lin."])
        ax.set_title(title.replace("\n", " "))
        ax.grid(axis="y")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("final test accuracy")
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig_summary")


# ---------------------------------------------------------------- Figure 6: depth sweep
def fig_depth():
    d = load("depth")
    depths = d["depths"]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    for a in ACT_ORDER:
        m = [np.mean(d["results"][str(k)][a]) for k in depths]
        s = [np.std(d["results"][str(k)][a], ddof=1) if len(d["results"][str(k)][a]) > 1 else 0 for k in depths]
        ax.errorbar(depths, m, yerr=s, color=COLOR[a], ls=STYLE[a], marker="o", ms=3.5, capsize=2, lw=1.4)
    ax.set_xscale("log", base=2)
    ax.set_xticks(depths)
    ax.set_xticklabels([str(k) for k in depths])
    ax.set_xlabel("hidden layers")
    ax.set_ylabel("test accuracy")
    ax.grid(axis="y")
    ax.legend(handles=legend_handles(), loc="lower left", fontsize=7)
    fig.tight_layout()
    save(fig, "fig_depth")


# ---------------------------------------------------------------- Figure 7: linearity + notch occupancy
def fig_linearity():
    d = load("linearity")
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.2))
    ax = axes[0]
    for i, a in enumerate(ACT_ORDER):
        v = np.array([r["linear_r2_trained"] for r in d["results"][a]])
        ax.bar(i, 1 - v.mean(), color=COLOR[a], width=0.62, lw=0)
        ax.scatter(np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v)), 1 - v, s=8, color=INK, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1e-7, 1)
    ax.set_xticks(range(4)); ax.set_xticklabels(["ReLU", "GELU", "HeLU", "Lin."])
    ax.set_ylabel("$1 - R^2$ of best linear fit")
    ax.set_title("Non-linearity of the trained network")
    ax.grid(axis="y"); ax.set_axisbelow(True)

    ax = axes[1]
    layers = len(d["results"]["helu"][0]["notch_frac_trained"])
    w = 0.38
    for j, key in enumerate(["notch_frac_init", "notch_frac_trained"]):
        v = np.array([r[key] for r in d["results"]["helu"]])  # seeds x layers
        ax.bar(np.arange(layers) + (j - 0.5) * w, 100 * v.mean(0), width=w - 0.04,
               color=COLOR["helu"], alpha=0.45 if j == 0 else 1.0, lw=0,
               label="at initialisation" if j == 0 else "after training")
    ax.set_xticks(range(layers)); ax.set_xticklabels([f"layer {k + 1}" for k in range(layers)])
    ax.set_ylabel("% pre-activations in $[0.5,0.6]$")
    ax.set_title("HeLU notch occupancy")
    ax.legend(loc="upper right")
    ax.grid(axis="y"); ax.set_axisbelow(True)
    fig.tight_layout(w_pad=2.0)
    save(fig, "fig_linearity")


# ---------------------------------------------------------------- LaTeX tables
def tables():
    out = []

    # Image benchmarks
    rows = []
    for n, title in [("mnist_mlp", "MNIST, MLP"), ("fashion_mlp", "Fashion-MNIST, MLP"), ("fashion_cnn", "Fashion-MNIST, CNN")]:
        d = load(n)
        acc = {a: [r["epoch_test_acc"][-1] for r in d["runs"][a]] for a in ACT_ORDER}
        t_r, p_r = welch(acc["helu"], acc["relu"])
        t_g, p_g = welch(acc["helu"], acc["gelu"])
        t_i, p_i = welch(acc["helu"], acc["identity"])
        rows.append(f"{title} & {ms(acc['relu'])} & {ms(acc['gelu'])} & {ms(acc['helu'])} & {ms(acc['identity'])} "
                    f"& {pfmt(p_r)} & {pfmt(p_g)} & {pfmt(p_i)} \\\\")
    out.append("% image benchmarks: final test accuracy, mean ± sd over seeds; Welch p-values HeLU vs others\n"
               "\\begin{tabular}{lcccccccc}\n\\toprule\n"
               " & \\multicolumn{4}{c}{Test accuracy (mean $\\pm$ sd)} & \\multicolumn{3}{c}{$p$ (HeLU vs.)} \\\\\n"
               "\\cmidrule(lr){2-5}\\cmidrule(lr){6-8}\n"
               "Benchmark & ReLU & GELU & HeLU & Linear & ReLU & GELU & Linear \\\\\n\\midrule\n"
               + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
    (GEN / "tab_image.tex").write_text(out[-1])

    # Wall time
    rows = []
    for n, title in [("mnist_mlp", "MNIST, MLP"), ("fashion_mlp", "Fashion-MNIST, MLP"), ("fashion_cnn", "Fashion-MNIST, CNN")]:
        d = load(n)
        cells = [f"{np.mean([r['wall_time_s'] for r in d['runs'][a]]) / d['epochs']:.1f}" for a in ACT_ORDER]
        rows.append(f"{title} & " + " & ".join(cells) + " \\\\")
    mb = load("microbench")
    cells = [f"{mb['results'][a]['mean_ms']:.1f}" for a in ACT_ORDER]
    rows.append(f"\\midrule Activation kernel, fwd+bwd, {mb['n'] / 1e6:.0f}M elements (ms) & " + " & ".join(cells) + " \\\\")
    (GEN / "tab_time.tex").write_text(
        "\\begin{tabular}{lcccc}\n\\toprule\n & ReLU & GELU & HeLU & Linear \\\\\n\\midrule\n"
        + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # 1-D regression
    d = load("reg1d")
    rows = []
    for t in d["targets"]:
        r = d["results"][t]
        name = f"${t}$" if t != "step" else "$\\mathbf{1}[x>0]$"
        rows.append(f"{name} & " + " & ".join(
            f"{np.mean(r[a]):.4f} $\\pm$ {np.std(r[a], ddof=1):.4f}" for a in ACT_ORDER) + " \\\\")
    (GEN / "tab_reg1d.tex").write_text(
        "\\begin{tabular}{lcccc}\n\\toprule\nTarget & ReLU & GELU & HeLU & Linear \\\\\n\\midrule\n"
        + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # 2-D classification
    d = load("cls2d")
    rows = []
    for ds in d["datasets"]:
        r = d["results"][ds]
        _, p_r = welch(r["helu"], r["relu"])
        _, p_g = welch(r["helu"], r["gelu"])
        rows.append(f"{ds} & " + " & ".join(ms(r[a]) for a in ACT_ORDER) + f" & {pfmt(p_r)} & {pfmt(p_g)} \\\\")
    (GEN / "tab_cls2d.tex").write_text(
        "\\begin{tabular}{lcccccc}\n\\toprule\n & \\multicolumn{4}{c}{Test accuracy} & \\multicolumn{2}{c}{$p$ (HeLU vs.)} \\\\\n"
        "\\cmidrule(lr){2-5}\\cmidrule(lr){6-7}\nDataset & ReLU & GELU & HeLU & Linear & ReLU & GELU \\\\\n\\midrule\n"
        + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # Depth
    d = load("depth")
    rows = []
    for k in d["depths"]:
        rows.append(f"{k} & " + " & ".join(ms(d["results"][str(k)][a]) for a in ACT_ORDER) + " \\\\")
    (GEN / "tab_depth.tex").write_text(
        "\\begin{tabular}{lcccc}\n\\toprule\nHidden layers & ReLU & GELU & HeLU & Linear \\\\\n\\midrule\n"
        + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # Linearity
    d = load("linearity")
    rows = []
    for a in ACT_ORDER:
        rs = d["results"][a]
        r2i = np.mean([r["linear_r2_init"] for r in rs])
        r2t = np.mean([r["linear_r2_trained"] for r in rs])
        ni = 100 * np.mean([np.mean(r["notch_frac_init"]) for r in rs])
        nt = 100 * np.mean([np.mean(r["notch_frac_trained"]) for r in rs])
        acc = np.mean([r["test_acc"] for r in rs])
        rows.append(f"{ACT_LABEL[a]} & {acc:.4f} & {r2i:.5f} & {r2t:.5f} & {ni:.2f} & {nt:.2f} \\\\")
    (GEN / "tab_linearity.tex").write_text(
        "\\begin{tabular}{lccccc}\n\\toprule\n & & \\multicolumn{2}{c}{$R^2$ of linear fit} & \\multicolumn{2}{c}{\\% pre-act.\\ in $[0.5,0.6]$} \\\\\n"
        "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\nActivation & Test acc. & init & trained & init & trained \\\\\n\\midrule\n"
        + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

    # A few headline numbers as macros for the prose.
    macros = []
    for n, key in [("mnist_mlp", "MnistMlp"), ("fashion_mlp", "FashionMlp"), ("fashion_cnn", "FashionCnn")]:
        dd = load(n)
        for a in ACT_ORDER:
            v = np.mean([r["epoch_test_acc"][-1] for r in dd["runs"][a]])
            macros.append(f"\\newcommand{{\\acc{key}{a.capitalize()}}}{{{100 * v:.2f}}}")
    d = load("linearity")
    macros.append("\\newcommand{\\rTwoHelu}{%.5f}" % np.mean([r["linear_r2_trained"] for r in d["results"]["helu"]]))
    macros.append("\\newcommand{\\rTwoRelu}{%.3f}" % np.mean([r["linear_r2_trained"] for r in d["results"]["relu"]]))
    macros.append("\\newcommand{\\notchHelu}{%.2f}" % (100 * np.mean([np.mean(r["notch_frac_trained"]) for r in d["results"]["helu"]])))
    d = load("cls2d")
    for ds in d["datasets"]:
        for a in ACT_ORDER:
            macros.append(f"\\newcommand{{\\acc{ds.capitalize()}{a.capitalize()}}}{{{100 * np.mean(d['results'][ds][a]):.1f}}}")
    (GEN / "macros.tex").write_text("\n".join(macros) + "\n")
    print("wrote tables + macros")


if __name__ == "__main__":
    fig_activation()
    fig_reg1d()
    fig_cls2d()
    fig_curves()
    fig_summary()
    fig_depth()
    fig_linearity()
    tables()
