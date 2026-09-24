"""Model definitions. Every model takes the activation *name* so the same
architecture is reused verbatim across ReLU / GELU / HeLU / Identity."""
from __future__ import annotations

import torch
import torch.nn as nn

from .activations import make_activation


class MLP(nn.Module):
    def __init__(self, in_dim: int, hidden: int, out_dim: int, depth: int, act: str):
        """`depth` = number of hidden layers (each followed by the activation)."""
        super().__init__()
        layers: list[nn.Module] = []
        d = in_dim
        for _ in range(depth):
            layers.append(nn.Linear(d, hidden))
            layers.append(make_activation(act))
            d = hidden
        layers.append(nn.Linear(d, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x.flatten(1) if x.dim() > 2 else x)

    def pre_activations(self, x: torch.Tensor) -> list[torch.Tensor]:
        """Return the input to every activation module (for notch-occupancy analysis)."""
        outs = []
        h = x.flatten(1) if x.dim() > 2 else x
        for m in self.net:
            if isinstance(m, nn.Linear):
                h = m(h)
            else:
                outs.append(h)
                h = m(h)
        return outs


class SmallCNN(nn.Module):
    """LeNet-style CNN for 28x28 grayscale inputs."""

    def __init__(self, act: str, n_classes: int = 10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            make_activation(act),
            nn.MaxPool2d(2),          # 14x14
            nn.Conv2d(32, 64, 3, padding=1),
            make_activation(act),
            nn.MaxPool2d(2),          # 7x7
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128),
            make_activation(act),
            nn.Linear(128, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))
