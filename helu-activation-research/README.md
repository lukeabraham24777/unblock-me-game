# HeLU activation study

An empirical comparison of three activation functions in small neural networks:

| name | definition |
|---|---|
| ReLU | `max(0, x)` |
| GELU | `x * Phi(x)` |
| **HeLU** | `x`, except `0.9 x` for `0.5 <= x <= 0.6` |

A fourth, **Identity** (no non-linearity), is included as a control because HeLU is
the identity map everywhere outside a narrow notch.

The write-up is a LaTeX paper in `paper/` with all figures produced by `make_figures.py`.

## Layout

```
helu-activation-research/
├── helu_research/
│   ├── activations.py   # ReLU / GELU / HeLU / Identity
│   ├── models.py        # MLP, small CNN
│   └── experiments.py   # every experiment as a function returning a dict
├── run_all.py           # runs experiments -> results/*.json
├── make_figures.py      # results/*.json -> figures/*.pdf|png + paper/generated/*.tex
├── results/             # JSON results (committed)
├── figures/             # PDF + PNG figures (committed)
├── paper/
│   ├── paper.tex, refs.bib, Makefile
│   ├── generated/       # tables & macros written by make_figures.py
│   └── paper.pdf
└── data/                # MNIST / Fashion-MNIST download cache (git-ignored)
```

## Reproduce

```bash
pip install -r requirements.txt
python run_all.py            # ~35 min on 4 CPU cores; add --quick for a 2-min smoke test
python make_figures.py
cd paper && make             # needs pdflatex + bibtex (texlive-latex-extra)
```

Experiments (all CPU, seeded):

1. `shape` – the functions and derivatives (analytic).
2. `reg1d` – 1-D regression of `sin(3x)`, `|x|`, `x^2`, step; MLP 1-64-64-1, 5 seeds.
3. `cls2d` – two-moons and two-spirals classification; MLP 2-64-64-2, 5 seeds.
4. `mnist_mlp`, `fashion_mlp` – 784-256-256-10 MLP, 5 epochs, 5 seeds.
5. `fashion_cnn` – 2-conv CNN, 5 epochs, 3 seeds.
6. `depth` – Fashion-MNIST MLP with 1/2/4/8 hidden layers.
7. `linearity` – how linear is each trained network? (`R^2` of a least-squares linear fit) and
   what fraction of HeLU pre-activations fall inside the notch.
8. `microbench` – forward+backward kernel time of the activation alone.
9. `variants` – 16 variants of the notch (moved to `[0.1,0.2]` or `[-0.05,0.05]`, deepened to
   scale 0.8/0.5/0.2, widened to `[0.5,1]`, `[0.5,2]`, `[0.5,inf)`, or a symmetric band
   `[-0.68,0.68]` at scale 0.5), each run on `sin(3x)`, `x^2`,
   moons, spirals and the Fashion-MNIST MLP. See `HELU_VARIANTS` in `helu_research/activations.py`.
   Run alone with `python run_all.py variants`.
10. `variant_occupancy` – band occupancy and linear-fit `R^2` on Fashion-MNIST for the original notch
    and the three widened variants (explains why only the half-line variant becomes non-linear).
11. `stair` – the staircase `y = 2*floor(x/2)` (value `k` on each `[k, k+2)`), exactly as defined
    (zero gradient almost everywhere) and with a straight-through estimator, on the same tasks as
    the variants. See `Stair` in `helu_research/activations.py`.
