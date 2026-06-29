"""
Activity 3.d - extend the model AFTER the data is loaded.

 (i)  add paymentMethod / isPromotional / satisfaction to every transaction
      (server-side, one pass, using $rand).
 (ii) materialize the "frequent collaborators" relationship:
      customers with >=5 tx at the same terminal AND avg satisfaction within 0.5.

    python src/extend.py --dataset D1
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db, PAYMENT_METHODS


def extend_transactions(db):
    """3.d.i - random payment method, promo flag, satisfaction rating (1..5)."""
    db.transactions.update_many({}, [{"$set": {
        "paymentMethod": {"$arrayElemAt": [
            PAYMENT_METHODS,
            {"$toInt": {"$floor": {"$multiply": [{"$rand": {}}, len(PAYMENT_METHODS)]}}}]},
        "isPromotional": {"$lt": [{"$rand": {}}, 0.3]},
        "satisfaction": {"$toInt": {"$add": [
            1, {"$floor": {"$multiply": [{"$rand": {}}, 5]}}]}},
    }}])


def build_frequent_collaborators(db):
    """3.d.ii - queryable Customer-Customer relationship."""
    db.frequent_collaborators.drop()
    per_term = db.transactions.aggregate([
        {"$group": {"_id": {"c": "$customerId", "t": "$terminalId"},
                    "n": {"$sum": 1}, "avgSat": {"$avg": "$satisfaction"}}},
        {"$match": {"n": {"$gte": 5}}},
        {"$group": {"_id": "$_id.t",
                    "members": {"$push": {"c": "$_id.c", "avgSat": "$avgSat"}}}}],
        allowDiskUse=True)
    edges = []
    for t in per_term:
        m = t["members"]
        for i in range(len(m)):
            for j in range(i + 1, len(m)):
                if abs(m[i]["avgSat"] - m[j]["avgSat"]) <= 0.5:
                    edges.append({"a": m[i]["c"], "b": m[j]["c"], "terminal": t["_id"],
                                  "avgSatA": round(m[i]["avgSat"], 3),
                                  "avgSatB": round(m[j]["avgSat"], 3)})
    if edges:
        db.frequent_collaborators.insert_many(edges)
    db.frequent_collaborators.create_index([("a", 1)])
    db.frequent_collaborators.create_index([("b", 1)])
    return len(edges)


def main(dataset):
    db = get_db(dataset)
    t0 = time.perf_counter()
    extend_transactions(db)
    n = build_frequent_collaborators(db)
    print(f"[{dataset}] extended tx + {n:,} collaborator edges "
          f"in {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    main(ap.parse_args().dataset)
