#!/usr/bin/env python3
"""Run every experiment and write results/<name>.json.

Usage:
    python run_all.py                 # everything
    python run_all.py shape reg2d     # a subset
    python run_all.py --quick         # tiny settings for a smoke test
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

from helu_research import experiments as E

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
DATA = str(ROOT / "data")


def save(name: str, obj: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / f"{name}.json", "w") as f:
        json.dump(obj, f)
    print(f"-> wrote results/{name}.json", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help="subset of experiment names")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    q = args.quick

    jobs = {
        "shape": lambda: E.run_activation_shape(),
        "reg1d": lambda: E.run_regression_1d(seeds=(0,) if q else (0, 1, 2, 3, 4), steps=200 if q else 3000),
        "cls2d": lambda: E.run_classification_2d(seeds=(0,) if q else (0, 1, 2, 3, 4), steps=200 if q else 3000),
        "mnist_mlp": lambda: E.run_image("mnist", "mlp", DATA, seeds=(0,) if q else (0, 1, 2, 3, 4),
                                         epochs=1 if q else 5),
        "fashion_mlp": lambda: E.run_image("fashion", "mlp", DATA, seeds=(0,) if q else (0, 1, 2, 3, 4),
                                           epochs=1 if q else 5),
        "fashion_cnn": lambda: E.run_image("fashion", "cnn", DATA, seeds=(0,) if q else (0, 1, 2),
                                           epochs=1 if q else 5),
        "depth": lambda: E.run_depth_sweep(DATA, depths=(1, 2) if q else (1, 2, 4, 8), seeds=(0,) if q else (0, 1, 2),
                                           epochs=1 if q else 3),
        "linearity": lambda: E.run_linearity(DATA, seeds=(0,) if q else (0, 1, 2), epochs=1 if q else 3),
        "microbench": lambda: E.run_microbench(n=100_000 if q else 4_000_000, reps=5 if q else 20),
        "variants": lambda: E.run_variants(DATA, seeds=(0,) if q else (0, 1, 2), steps=200 if q else 3000,
                                           epochs=1 if q else 3),
        "variant_occupancy": lambda: E.run_variant_occupancy(DATA, seeds=(0,) if q else (0, 1, 2), epochs=1 if q else 3),
        "sawtooth": lambda: E.run_extra(DATA, names=("sawtooth",), seeds=(0,) if q else (0, 1, 2),
                                        steps=200 if q else 3000, epochs=1 if q else 3),
        "sawtooth_diag": lambda: E.run_sawtooth_diagnostics(DATA, seeds=(0,) if q else (0, 1, 2),
                                                            steps=200 if q else 3000, epochs=1 if q else 3),
        "stepslope": lambda: E.run_extra(DATA, names=tuple(__import__("helu_research.activations", fromlist=["x"]).STEPSLOPE_VARIANTS),
                                         seeds=(0,) if q else (0, 1, 2), steps=200 if q else 3000, epochs=1 if q else 3),
        "stepslope_tune": lambda: E.run_stepslope_tune(DATA, widths=(1.0,) if q else (0.5, 1.0, 2.0),
                                                       deltas=(1.0,) if q else (0.5, 1.0, 2.0, 4.0),
                                                       seeds=(0,) if q else (0, 1, 2), epochs=1 if q else 3,
                                                       steps=200 if q else 3000),
        "stepslope_final": lambda: E.run_stepslope_final(
            DATA, best=json.load(open(RESULTS / "stepslope_tune.json"))["best"],
            mlp_seeds=(0,) if q else (0, 1, 2, 3, 4), cnn_seeds=(0,) if q else (0, 1, 2), epochs=1 if q else 5),
    }
    names = args.only or list(jobs)
    unknown = [n for n in names if n not in jobs]
    if unknown:
        sys.exit(f"unknown experiment(s): {unknown}; choose from {list(jobs)}")
    t_all = time.time()
    for n in names:
        print(f"=== {n} ===", flush=True)
        t0 = time.time()
        save(n, jobs[n]())
        print(f"=== {n} done in {time.time() - t0:.0f}s ===", flush=True)
    print(f"all done in {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()
