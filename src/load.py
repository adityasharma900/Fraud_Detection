"""
Activity 4 - load a generated dataset into MongoDB.

Bulk insert in batches, build indexes AFTER loading (faster), and store the
pre-computed time fields (year/quarter/dayOfWeek) and the isOutlier flag used
by queries (b) and (e). Returns the wall-clock load time for the benchmark.

    python src/load.py --dataset D1
"""
import argparse
import os
import sys
import time

import pandas as pd
from pymongo import InsertOne

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db, data_dir


def build_indexes(db):
    db.transactions.create_index([("customerId", 1)])
    db.transactions.create_index([("terminalId", 1), ("datetime", 1)])
    db.transactions.create_index([("quarter", 1)])
    db.transactions.create_index([("terminalId", 1), ("customerId", 1)])
    db.customers.create_index([("availableTerminals", 1)])      # multikey
    db.customers.create_index([("location", "2dsphere")])       # geospatial
    db.terminals.create_index([("location", "2dsphere")])


def load(dataset, batch=10_000):
    db = get_db(dataset)
    for c in ("customers", "terminals", "transactions",
              "customer_terminals", "cocustomer_adj",
              "terminal_prev_median", "frequent_collaborators", "alerts"):
        db[c].drop()

    d = data_dir(dataset)
    t0 = time.perf_counter()

    # terminals -------------------------------------------------------------
    term = pd.read_parquet(os.path.join(d, "terminals.parquet"))
    db.terminals.insert_many([
        {"_id": int(r.TERMINAL_ID),
         "location": {"type": "Point",
                      "coordinates": [float(r.x_terminal_id), float(r.y_terminal_id)]}}
        for r in term.itertuples()], ordered=False)

    # customers -------------------------------------------------------------
    cust = pd.read_parquet(os.path.join(d, "customers.parquet"))
    db.customers.insert_many([
        {"_id": int(r.CUSTOMER_ID), "name": r.name,
         "location": {"type": "Point",
                      "coordinates": [float(r.x_customer_id), float(r.y_customer_id)]},
         "meanAmount": float(r.mean_amount), "stdAmount": float(r.std_amount),
         "meanNbTxPerDay": float(r.mean_nb_tx_per_day),
         "availableTerminals": [int(t) for t in r.available_terminals],
         "nbTerminals": int(r.nb_terminals)} for r in cust.itertuples()], ordered=False)

    # transactions (streamed in batches) ------------------------------------
    tx = pd.read_parquet(os.path.join(d, "transactions.parquet"))
    tx["datetime"] = pd.to_datetime(tx["TX_DATETIME"])
    ops = []
    for r in tx.itertuples():
        dt = r.datetime
        ops.append(InsertOne({
            "_id": int(r.TRANSACTION_ID), "customerId": int(r.CUSTOMER_ID),
            "terminalId": int(r.TERMINAL_ID), "datetime": dt.to_pydatetime(),
            "amount": float(r.TX_AMOUNT), "fraud": int(r.TX_FRAUD),
            "fraudScenario": int(r.TX_FRAUD_SCENARIO),
            "year": int(dt.year), "quarter": (int(dt.month) - 1) // 3 + 1,
            "dayOfWeek": int(dt.isoweekday()), "isOutlier": False}))
        if len(ops) == batch:
            db.transactions.bulk_write(ops, ordered=False); ops = []
    if ops:
        db.transactions.bulk_write(ops, ordered=False)

    build_indexes(db)
    elapsed = time.perf_counter() - t0
    print(f"[{dataset}] loaded {db.transactions.estimated_document_count():,} tx "
          f"in {elapsed:.1f}s")
    return elapsed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    load(ap.parse_args().dataset)
