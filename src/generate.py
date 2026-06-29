"""
Activity 1 - dataset generation.

Wraps the handbook simulator and patches in the synthetic `name` field that the
simulator does not produce but query (a) requires. Writes three tables per
dataset to parquet plus a meta.json recording parameters and measured size.

    python src/generate.py --all
    python src/generate.py --dataset D1
    python src/generate.py --sample            # tiny set for tests/oracle
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from faker import Faker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATASETS, SAMPLE, SEED, START_DATE, RADIUS, data_dir
from simulator import (generate_customer_profiles_table,
                       generate_terminal_profiles_table,
                       get_list_terminals_within_radius,
                       generate_transactions_table, add_frauds)


def generate_dataset(n_customers, n_terminals, nb_days, r=RADIUS,
                     start_date=START_DATE, seed=SEED):
    fake = Faker()
    Faker.seed(seed)

    customers = generate_customer_profiles_table(n_customers, random_state=seed)
    terminals = generate_terminal_profiles_table(n_terminals, random_state=seed + 1)

    # Geographic reachability -> available_terminals.
    x_y_terminals = terminals[["x_terminal_id", "y_terminal_id"]].values.astype(float)
    customers["available_terminals"] = customers.apply(
        lambda c: get_list_terminals_within_radius(c, x_y_terminals, r), axis=1)
    customers["nb_terminals"] = customers["available_terminals"].apply(len)

    # PATCH: query (a) asks for customer names, which the simulator omits.
    customers["name"] = [fake.name() for _ in range(len(customers))]

    # Transactions per customer, then assign a global TRANSACTION_ID.
    parts = []
    for _, c in customers.iterrows():
        parts.append(generate_transactions_table(c, start_date, nb_days))
    tx = pd.concat(parts, ignore_index=True)
    tx = add_frauds(customers, terminals, tx)
    tx = tx.sort_values("TX_DATETIME").reset_index(drop=True)
    tx.insert(0, "TRANSACTION_ID", tx.index)

    return customers, terminals, tx


def write_dataset(name, customers, terminals, tx, params):
    d = data_dir(name)
    os.makedirs(d, exist_ok=True)
    # available_terminals is a list -> keep it as a python object column.
    customers.to_parquet(os.path.join(d, "customers.parquet"))
    terminals.to_parquet(os.path.join(d, "terminals.parquet"))
    tx.to_parquet(os.path.join(d, "transactions.parquet"))

    size_mb = os.path.getsize(os.path.join(d, "transactions.parquet")) / 1e6
    meta = {**params, "tx_rows": int(len(tx)),
            "n_customers": int(len(customers)), "n_terminals": int(len(terminals)),
            "fraud_rate": round(float(tx.TX_FRAUD.mean()), 4),
            "size_mb_parquet": round(size_mb, 2)}
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=2)
    print(f"[{name}] {meta['tx_rows']:,} tx  |  {size_mb:.1f} MB parquet  "
          f"|  fraud={meta['fraud_rate']}")
    return meta


def build(name, params):
    np.random.seed(SEED)
    customers, terminals, tx = generate_dataset(
        params["n_customers"], params["n_terminals"], params["nb_days"])
    return write_dataset(name, customers, terminals, tx, params)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=list(DATASETS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()

    if args.sample:
        build("SAMPLE", SAMPLE)
    elif args.all:
        for name, params in DATASETS.items():
            build(name, params)
    elif args.dataset:
        build(args.dataset, DATASETS[args.dataset])
    else:
        ap.error("choose --all, --dataset Dx, or --sample")


if __name__ == "__main__":
    main()
