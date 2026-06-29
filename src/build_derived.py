"""
Build the derived collections that accelerate the heavy operations
(Computed Pattern + materialized graph). Run after load.py.

    python src/build_derived.py --dataset D1
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db


def build_customer_terminals(db):
    """Per customer: distinct terminals used + total tx count (Computed Pattern)."""
    db.customer_terminals.drop()
    db.transactions.aggregate([
        {"$group": {"_id": "$customerId",
                    "terminals": {"$addToSet": "$terminalId"},
                    "txCount": {"$sum": 1}}},
        {"$set": {"nTerminals": {"$size": "$terminals"}}},
        {"$merge": {"into": "customer_terminals"}}], allowDiskUse=True)


def build_cocustomer_adj(db):
    """Adjacency list: customer -> customers sharing >=1 terminal (for $graphLookup)."""
    db.cocustomer_adj.drop()
    db.transactions.aggregate([
        {"$group": {"_id": "$terminalId", "custs": {"$addToSet": "$customerId"}}},
        {"$unwind": "$custs"},
        {"$project": {"cust": "$custs",
                      "others": {"$setDifference": ["$custs", ["$custs"]]}}},
        {"$unwind": "$others"},
        {"$group": {"_id": "$cust", "neighbors": {"$addToSet": "$others"}}},
        {"$merge": {"into": "cocustomer_adj"}}], allowDiskUse=True)


def main(dataset):
    db = get_db(dataset)
    build_customer_terminals(db)
    build_cocustomer_adj(db)
    print(f"[{dataset}] derived: customer_terminals="
          f"{db.customer_terminals.estimated_document_count():,}, "
          f"cocustomer_adj={db.cocustomer_adj.estimated_document_count():,}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    main(ap.parse_args().dataset)
