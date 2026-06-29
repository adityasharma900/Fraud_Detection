"""
Activity 5 - measure execution times for every operation (incl. load and the
3.d update) across D1/D2/D3, write results/timings.csv and report figures.

    python src/benchmark.py --all
"""
import argparse
import csv
import os
import statistics
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db, DATASETS
import load as load_mod
import build_derived
import extend
import queries

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
FIGS = os.path.join(ROOT, "report", "figures")


def timed(fn, *a, repeats=3, **k):
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter(); fn(*a, **k); ts.append(time.perf_counter() - t0)
    return {"mean": statistics.mean(ts), "best": min(ts)}


def bench_dataset(ds):
    db = get_db(ds)
    rows = []
    # one-time builds (timed once)
    rows.append(("load", ds, timed(load_mod.load, ds, repeats=1)))
    rows.append(("derive", ds, timed(build_derived.main, ds, repeats=1)))
    rows.append(("extend(3.d)", ds, timed(extend.main, ds, repeats=1)))
    # queries (repeated)
    m0 = db.customer_terminals.find_one()["_id"]
    u0 = db.cocustomer_adj.find_one()["_id"]
    rows.append(("q_a", ds, timed(queries.query_a, db, m0)))
    rows.append(("q_b", ds, timed(queries.query_b, db)))
    rows.append(("q_c", ds, timed(queries.query_c, db, u0, k=3)))
    rows.append(("q_e", ds, timed(queries.query_e, db)))
    return rows


def run(datasets):
    os.makedirs(RESULTS, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)
    flat = []
    for ds in datasets:
        for op, d, t in bench_dataset(ds):
            flat.append({"dataset": ds, "op": op, "mean_s": round(t["mean"], 4),
                         "best_s": round(t["best"], 4)})
    with open(os.path.join(RESULTS, "timings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataset", "op", "mean_s", "best_s"])
        w.writeheader(); w.writerows(flat)
    make_figures(flat, datasets)
    print(f"wrote {RESULTS}/timings.csv and figures in {FIGS}")
    return flat


def make_figures(flat, datasets):
    ops = sorted({r["op"] for r in flat if r["op"].startswith("q_")})
    # grouped bars: query time per dataset
    fig, ax = plt.subplots(figsize=(8, 4.5))
    width = 0.8 / len(datasets)
    for i, ds in enumerate(datasets):
        vals = [next((r["mean_s"] for r in flat if r["op"] == op and r["dataset"] == ds), 0)
                for op in ops]
        ax.bar([x + i * width for x in range(len(ops))], vals, width, label=ds)
    ax.set_xticks([x + width for x in range(len(ops))]); ax.set_xticklabels(ops)
    ax.set_ylabel("mean time (s)"); ax.set_title("Query time by dataset"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "query_times.png"), dpi=130)

    # load time vs dataset size
    fig, ax = plt.subplots(figsize=(6, 4))
    sizes = [DATASETS.get(ds, {}).get("target_mb", 0) for ds in datasets]
    loads = [next((r["mean_s"] for r in flat if r["op"] == "load" and r["dataset"] == ds), 0)
             for ds in datasets]
    ax.plot(sizes, loads, "o-"); ax.set_xlabel("dataset target (MB)")
    ax.set_ylabel("load time (s)"); ax.set_title("Load time vs dataset size")
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "load_times.png"), dpi=130)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--datasets", nargs="*", default=None)
    args = ap.parse_args()
    run(args.datasets or (list(DATASETS) if args.all else ["D1"]))
