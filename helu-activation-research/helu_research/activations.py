"""Activation functions under study.

HeLU is defined as

    y = x            for x < 0.5 or x > 0.6
    y = 0.9 * x      for 0.5 <= x <= 0.6

i.e. the identity map with a narrow "notch" in which the output is scaled by 0.9.
It is discontinuous at both edges of the notch (jump of -0.05 at x = 0.5 and
+0.06 at x = 0.6) and its derivative is 1 everywhere except inside the notch,
where it is 0.9.
"""
from __future__ import annotations

import re

import torch
import torch.nn as nn
import torch.nn.functional as F

HELU_LO = 0.5
HELU_HI = 0.6
HELU_SCALE = 0.9


def helu(x: torch.Tensor, lo: float = HELU_LO, hi: float = HELU_HI, scale: float = HELU_SCALE) -> torch.Tensor:
    """Functional HeLU. Autograd yields d/dx = `scale` inside the notch, 1 elsewhere.

    The defaults give the original definition; other (lo, hi, scale) give the
    variants studied in the ablation (`experiments.run_variants`)."""
    in_notch = (x >= lo) & (x <= hi)
    return torch.where(in_notch, scale * x, x)


class HeLU(nn.Module):
    def __init__(self, lo: float = HELU_LO, hi: float = HELU_HI, scale: float = HELU_SCALE):
        super().__init__()
        self.lo, self.hi, self.scale = float(lo), float(hi), float(scale)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # noqa: D401
        return helu(x, self.lo, self.hi, self.scale)

    def extra_repr(self) -> str:
        return f"notch=[{self.lo}, {self.hi}], scale={self.scale}"


# Variants of the notch for the ablation. Name -> (lo, hi, scale).
# The original is "helu"; the others move the notch, deepen it, or widen it.
HELU_VARIANTS: dict[str, tuple[float, float, float]] = {
    # original position, deeper notches
    "n0.5-0.6_s0.9": (0.5, 0.6, 0.9),
    "n0.5-0.6_s0.8": (0.5, 0.6, 0.8),
    "n0.5-0.6_s0.5": (0.5, 0.6, 0.5),
    "n0.5-0.6_s0.2": (0.5, 0.6, 0.2),
    # notch moved to [0.1, 0.2]
    "n0.1-0.2_s0.9": (0.1, 0.2, 0.9),
    "n0.1-0.2_s0.8": (0.1, 0.2, 0.8),
    "n0.1-0.2_s0.5": (0.1, 0.2, 0.5),
    "n0.1-0.2_s0.2": (0.1, 0.2, 0.2),
    # notch straddling zero
    "n-0.05-0.05_s0.9": (-0.05, 0.05, 0.9),
    "n-0.05-0.05_s0.8": (-0.05, 0.05, 0.8),
    "n-0.05-0.05_s0.5": (-0.05, 0.05, 0.5),
    "n-0.05-0.05_s0.2": (-0.05, 0.05, 0.2),
    # wider notches at scale 0.2, starting at 0.5
    "n0.5-1.0_s0.2": (0.5, 1.0, 0.2),
    "n0.5-2.0_s0.2": (0.5, 2.0, 0.2),
    "n0.5-inf_s0.2": (0.5, float("inf"), 0.2),
    # wide symmetric band around zero, halved inside
    "n-0.68-0.68_s0.5": (-0.68, 0.68, 0.5),
}


def variant_label(name: str) -> str:
    lo, hi, s = HELU_VARIANTS[name]
    hi_s = "∞" if hi == float("inf") else f"{hi:g}"
    return f"[{lo:g}, {hi_s}] × {s:g}"


class Identity(nn.Module):
    """Linear control: no non-linearity at all (a deep linear network)."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


# Sawtooth function --------------------------------------------------------
SAW_PERIOD = 2.0


def sawtooth(x: torch.Tensor, period: float = SAW_PERIOD) -> torch.Tensor:
    """On each interval [k, k + period), k a multiple of `period`, a straight line from
    (k, 0) to (k + period, 1):  y = (x - k) / period = x / period - floor(x / period).

    Derivative is 1 / period almost everywhere; the function drops by 1 at every multiple of `period`."""
    return x / period - torch.floor(x / period)


class Sawtooth(nn.Module):
    def __init__(self, period: float = SAW_PERIOD):
        super().__init__()
        self.period = float(period)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return sawtooth(x, self.period)

    def extra_repr(self) -> str:
        return f"period={self.period}"


# Slope-stepping piecewise-linear function ---------------------------------
def stepslope(x: torch.Tensor, width: float = 1.0, delta: float = 0.01) -> torch.Tensor:
    """Continuous piecewise-linear function whose slope on segment k = floor(x / width) is 1 + delta * k,
    for every integer k (so the slope steps up by `delta` at each boundary, and the function is convex).

    Closed form: f(x) = x + delta * [ width * k (k - 1) / 2 + k (x - k * width) ],  k = floor(x / width).
    Equivalent to a piecewise-linear approximation of x + delta * x^2 / (2 width)."""
    k = torch.floor(x / width)
    return x + delta * (width * k * (k - 1) / 2 + k * (x - k * width))


class StepSlope(nn.Module):
    def __init__(self, width: float = 1.0, delta: float = 0.01):
        super().__init__()
        self.width, self.delta = float(width), float(delta)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return stepslope(x, self.width, self.delta)

    def extra_repr(self) -> str:
        return f"width={self.width}, delta={self.delta}"


# name -> (width, delta)
STEPSLOPE_VARIANTS: dict[str, tuple[float, float]] = {
    "ss_w1_d0.01": (1.0, 0.01),    # as proposed
    "ss_w1_d0.1": (1.0, 0.1),
    "ss_w1_d1": (1.0, 1.0),
    "ss_w0.1_d0.1": (0.1, 0.1),    # same curvature as (1, 1) but ten times finer segments
}


_SS_RE = re.compile(r"^ss_w(?P<w>[0-9.]+)_d(?P<d>[0-9.]+)$")


def stepslope_params(name: str) -> tuple[float, float] | None:
    """(width, delta) for a name of the form ss_w<W>_d<delta>, else None."""
    if name in STEPSLOPE_VARIANTS:
        return STEPSLOPE_VARIANTS[name]
    m = _SS_RE.match(name)
    return (float(m["w"]), float(m["d"])) if m else None


def stepslope_name(width: float, delta: float) -> str:
    return f"ss_w{width:g}_d{delta:g}"


def stepslope_label(name: str) -> str:
    w, d = stepslope_params(name)
    return f"W={w:g}, \u03b4={d:g}"


# Bounded-slope piecewise-linear family (sums of a few ReLUs) ---------------
# Each entry: list of (knot, slope_change). f(x) = sum_i slope_change_i * relu(x - knot_i).
# Slope is bounded by the sum of positive slope changes; every function is 0 for x below its first knot.
PWL_FAMILY: dict[str, list[tuple[float, float]]] = {
    # capped slope-stepper (W=2, delta=1, k clipped to [-1, 1]): ReLU with slope 2 beyond x=2
    "pwl_relukink2": [(0.0, 1.0), (2.0, 1.0)],
    # soft knee: slopes 0 / 0.5 / 1 with breaks at -1 and 0 (capped stepper W=1, delta=0.5, k in [-2, 0])
    "pwl_knee": [(-1.0, 0.5), (0.0, 0.5)],
    # four-step ramp from slope 0 to 1 over [-4, 0] (capped stepper W=1, delta=0.25, k in [-4, 0])
    "pwl_ramp4": [(-4.0, 0.25), (-3.0, 0.25), (-2.0, 0.25), (-1.0, 0.25)],
    # three-piece linear approximation of GELU (dip to about -0.17 at -0.75)
    "pwl_hgelu3": [(-2.5, -0.1), (-0.75, 0.3333), (0.0, 0.7667)],
    # four-piece linear approximation of GELU
    "pwl_hgelu4": [(-3.0, -0.085), (-1.0, 0.255), (0.0, 0.67), (1.0, 0.16)],
}

PWL_LABEL = {
    "pwl_relukink2": "ReLU-kink-2",
    "pwl_knee": "Knee",
    "pwl_ramp4": "Ramp-4",
    "pwl_hgelu3": "HardGELU-3",
    "pwl_hgelu4": "HardGELU-4",
}


def pwl(x: torch.Tensor, pieces) -> torch.Tensor:
    out = None
    for knot, dslope in pieces:
        term = dslope * F.relu(x - knot)
        out = term if out is None else out + term
    return out


class PWL(nn.Module):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.pieces = PWL_FAMILY[name]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return pwl(x, self.pieces)

    def extra_repr(self) -> str:
        return self.name


class HardSwish(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.hardswish(x)


# Registry ----------------------------------------------------------------
ACTIVATIONS = {
    "relu": nn.ReLU,
    "gelu": nn.GELU,
    "helu": HeLU,
    "identity": Identity,
    "sawtooth": Sawtooth,                            # periodic ramp 0 -> 1 on each [k, k+2)
    "hardswish": HardSwish,                          # reference cheap GELU/Swish approximation
}

# Order used everywhere (tables, figures, legends).
ACT_ORDER = ["relu", "gelu", "helu", "identity"]
ACT_LABEL = {"relu": "ReLU", "gelu": "GELU", "helu": "HeLU", "identity": "Identity (linear control)",
             "hardswish": "Hardswish", **PWL_LABEL}


def make_activation(name: str) -> nn.Module:
    if name in HELU_VARIANTS:
        return HeLU(*HELU_VARIANTS[name])
    if stepslope_params(name) is not None:
        return StepSlope(*stepslope_params(name))
    if name in PWL_FAMILY:
        return PWL(name)
    try:
        return ACTIVATIONS[name]()
    except KeyError as e:  # pragma: no cover
        raise ValueError(f"unknown activation {name!r}; choose from {list(ACTIVATIONS)}") from e


def activation_fn(name: str):
    """Return a plain callable for numpy-free evaluation in torch."""
    if name in HELU_VARIANTS:
        lo, hi, s = HELU_VARIANTS[name]
        return lambda t: helu(t, lo, hi, s)
    if stepslope_params(name) is not None:
        w, d = stepslope_params(name)
        return lambda t: stepslope(t, w, d)
    if name in PWL_FAMILY:
        pieces = PWL_FAMILY[name]
        return lambda t: pwl(t, pieces)
    return {
        "relu": F.relu,
        "gelu": F.gelu,
        "helu": helu,
        "identity": lambda t: t,
        "sawtooth": sawtooth,
        "hardswish": F.hardswish,
    }[name]
