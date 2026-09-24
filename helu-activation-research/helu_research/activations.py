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


def helu(x: torch.Tensor) -> torch.Tensor:
    """Functional HeLU. Autograd yields d/dx = 0.9 inside the notch, 1 elsewhere."""
    in_notch = (x >= HELU_LO) & (x <= HELU_HI)
    return torch.where(in_notch, HELU_SCALE * x, x)


class HeLU(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:  # noqa: D401
        return helu(x)


class Identity(nn.Module):
    """Linear control: no non-linearity at all (a deep linear network)."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


# Registry ----------------------------------------------------------------
ACTIVATIONS = {
    "relu": nn.ReLU,
    "gelu": nn.GELU,
    "helu": HeLU,
    "identity": Identity,
}

# Order used everywhere (tables, figures, legends).
ACT_ORDER = ["relu", "gelu", "helu", "identity"]
ACT_LABEL = {"relu": "ReLU", "gelu": "GELU", "helu": "HeLU", "identity": "Identity (linear control)"}


def make_activation(name: str) -> nn.Module:
    try:
        return ACTIVATIONS[name]()
    except KeyError as e:  # pragma: no cover
        raise ValueError(f"unknown activation {name!r}; choose from {list(ACTIVATIONS)}") from e


def activation_fn(name: str):
    """Return a plain callable for numpy-free evaluation in torch."""
    return {
        "relu": F.relu,
        "gelu": F.gelu,
        "helu": helu,
        "identity": lambda t: t,
    }[name]
