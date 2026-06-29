"""
Offline correctness oracle (NO MongoDB required).

Re-implements queries (a), (b), (c), (e) in pandas over the generated SAMPLE
dataset and prints the results. This is the independent reference used to
validate the MongoDB aggregation/$graphLookup implementations in queries.py:
the two must agree.

    python src/generate.py --sample
    python tests/oracle_pandas.py
"""
import os
import sys
from collections import defaultdict, deque

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from config import data_dir


def load():
    d = data_dir("SAMPLE")
    cust = pd.read_parquet(os.path.join(d, "customers.parquet"))
    tx = pd.read_parquet(os.path.join(d, "transactions.parquet"))
    tx["datetime"] = pd.to_datetime(tx["TX_DATETIME"])
    tx["year"] = tx.datetime.dt.year
    tx["quarter"] = tx.datetime.dt.quarter
    tx["dow"] = tx.datetime.dt.dayofweek + 1  # Mon=1..Sun=7 (matches load.py)
    return cust, tx


def cust_terminals(tx):
    g = tx.groupby("CUSTOMER_ID")["TERMINAL_ID"]
    terms = g.apply(lambda s: set(s.unique()))
    counts = tx.groupby("CUSTOMER_ID").size()
    return terms, counts


# 3.a -----------------------------------------------------------------------
def query_a(cust, tx, M, min_shared=4, tol=2):
    terms, counts = cust_terminals(tx)
    if M not in terms.index:
        return []
    out = []
    for N in terms.index:
        if N == M:
            continue
        shared = len(terms[M] & terms[N])
        if shared >= min_shared and abs(counts[M] - counts[N]) <= tol:
            out.append((M, N, shared, int(counts[M]), int(counts[N])))
    return out


# 3.b -----------------------------------------------------------------------
def query_b(tx, cur=(2024, 2), prev=(2024, 1), factor=1.3):
    prev_tx = tx[(tx.year == prev[0]) & (tx.quarter == prev[1])]
    med = prev_tx.groupby("TERMINAL_ID")["TX_AMOUNT"].median()
    cur_tx = tx[(tx.year == cur[0]) & (tx.quarter == cur[1])].copy()
    cur_tx["medPrev"] = cur_tx["TERMINAL_ID"].map(med)
    flagged = cur_tx[(cur_tx.medPrev.notna()) &
                     (cur_tx.TX_AMOUNT > factor * cur_tx.medPrev)]
    return flagged


# 3.c -----------------------------------------------------------------------
def query_c(tx, u, k=3):
    adj = defaultdict(set)
    for _, grp in tx.groupby("TERMINAL_ID")["CUSTOMER_ID"]:
        members = list(set(grp))
        for a in members:
            for b in members:
                if a != b:
                    adj[a].add(b)
    # BFS up to (k-1) hops; CC3 -> 2 hops
    seen, frontier = {u}, {u}
    for _ in range(k - 1):
        nxt = set()
        for x in frontier:
            nxt |= adj[x]
        nxt -= seen
        seen |= nxt
        frontier = nxt
    return seen - {u}


# 3.e -----------------------------------------------------------------------
def query_e(tx, flagged_ids):
    tx = tx.copy()
    tx["isOutlier"] = tx["TRANSACTION_ID"].isin(flagged_ids)
    g = tx.groupby("dow")
    res = pd.DataFrame({"total": g.size(),
                        "outliers": g["isOutlier"].sum()})
    res["outlierPct"] = (res["outliers"] / res["total"] * 100).round(2)
    return res.reset_index()


def main():
    cust, tx = load()
    terms, counts = cust_terminals(tx)
    print(f"SAMPLE: {len(cust)} customers, {tx.TERMINAL_ID.nunique()} terminals, "
          f"{len(tx)} tx, quarters={sorted(tx.quarter.unique())}")

    # pick an M with many terminals so 3.a can find matches
    M = counts.index[counts.argmax()]
    a = query_a(cust, tx, int(M))
    print(f"\n[3.a] M={M} (txCount={int(counts[M])}): {len(a)} similar customers")
    for row in a[:5]:
        print("   ", row)

    flagged = query_b(tx)
    print(f"\n[3.b] flagged outliers (Q1->Q2): {len(flagged)} "
          f"over {flagged.TERMINAL_ID.nunique()} terminals")

    u = int(terms.index[0])
    cc3 = query_c(tx, u, k=3)
    print(f"\n[3.c] CC3(u={u}): {len(cc3)} customers reachable in <=2 hops")

    e = query_e(tx, set(flagged.TRANSACTION_ID))
    print("\n[3.e] day-of-week summary:")
    print(e.to_string(index=False))

    # sanity assertions
    assert all(s >= 4 and abs(cm - cn) <= 2 for (_, _, s, cm, cn) in a)
    assert u not in cc3
    assert (e["outlierPct"] <= 100).all()
    print("\nAll oracle assertions passed.")


if __name__ == "__main__":
    main()
