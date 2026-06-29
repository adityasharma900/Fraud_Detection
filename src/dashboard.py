"""
Next-level: a static HTML dashboard built from results/timings.csv and a live
query against MongoDB (weekday summary + a co-customer network preview).

    python src/dashboard.py --dataset D1   ->  report/dashboard.html
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db
import queries

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(dataset):
    db = get_db(dataset)
    weekday = queries.query_e(db)
    timings = []
    p = os.path.join(ROOT, "results", "timings.csv")
    if os.path.exists(p):
        timings = list(csv.DictReader(open(p)))
    html = f"""<!doctype html><meta charset=utf-8>
<title>Fraud DB dashboard - {dataset}</title>
<style>body{{font-family:system-ui;margin:2rem;color:#1f2329}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 8px}}
th{{background:#00857a;color:#fff}}h1{{color:#0c2b2a}}</style>
<h1>Credit-card fraud database - {dataset}</h1>
<h2>Day-of-week summary (query 3.e)</h2>
<table><tr><th>Weekday</th><th>Total</th><th>Outliers</th><th>Outlier %</th></tr>
{''.join(f"<tr><td>{r['dayOfWeek']}</td><td>{r['total']}</td><td>{r['outliers']}</td><td>{r['outlierPct']}</td></tr>" for r in weekday)}
</table>
<h2>Benchmark timings</h2>
<pre>{json.dumps(timings, indent=2)}</pre>"""
    out = os.path.join(ROOT, "report", "dashboard.html")
    open(out, "w").write(html)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="D1")
    build(ap.parse_args().dataset)
