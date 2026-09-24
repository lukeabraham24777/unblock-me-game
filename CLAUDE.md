# Repository notes for Claude

This repository was originally created for the **Unblock Me** puzzle game
(Vite + TypeScript, see `README.md`, `src/`, `public/`). It is now also used, purely
for convenience, to host an unrelated research project.

## `helu-activation-research/` — the active project

All work on the activation-function study lives in **`helu-activation-research/`**
and should be treated as a self-contained project rooted at that folder. Do not
mix it with the game code and do not add its dependencies to `package.json`.

- `helu-activation-research/README.md` describes the project layout and how to run it.
- Python code is in `helu-activation-research/helu_research/` (CPU-only PyTorch).
- `run_all.py` runs the experiments -> `results/*.json`.
- `make_figures.py` renders `figures/` and the generated LaTeX tables in `paper/generated/`.
- The paper is `helu-activation-research/paper/paper.tex` (build with `make` in `paper/`).
- Downloaded datasets go in `helu-activation-research/data/` (git-ignored).

Work in that directory (`cd helu-activation-research`) for anything related to the
HeLU / ReLU / GELU comparison.
