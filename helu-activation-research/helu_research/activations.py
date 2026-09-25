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


# Registry ----------------------------------------------------------------
ACTIVATIONS = {
    "relu": nn.ReLU,
    "gelu": nn.GELU,
    "helu": HeLU,
    "identity": Identity,
    "sawtooth": Sawtooth,                            # periodic ramp 0 -> 1 on each [k, k+2)
}

# Order used everywhere (tables, figures, legends).
ACT_ORDER = ["relu", "gelu", "helu", "identity"]
ACT_LABEL = {"relu": "ReLU", "gelu": "GELU", "helu": "HeLU", "identity": "Identity (linear control)"}


def make_activation(name: str) -> nn.Module:
    if name in HELU_VARIANTS:
        return HeLU(*HELU_VARIANTS[name])
    try:
        return ACTIVATIONS[name]()
    except KeyError as e:  # pragma: no cover
        raise ValueError(f"unknown activation {name!r}; choose from {list(ACTIVATIONS)}") from e


def activation_fn(name: str):
    """Return a plain callable for numpy-free evaluation in torch."""
    if name in HELU_VARIANTS:
        lo, hi, s = HELU_VARIANTS[name]
        return lambda t: helu(t, lo, hi, s)
    return {
        "relu": F.relu,
        "gelu": F.gelu,
        "helu": helu,
        "identity": lambda t: t,
        "sawtooth": sawtooth,
    }[name]
