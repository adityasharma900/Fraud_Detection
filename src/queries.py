"""
Activity 3 (a-e) - the five required operations, implemented with the MongoDB
aggregation framework and $graphLookup. Each function returns its result so the
benchmark and tests can consume it.

    python src/queries.py --dataset D1 --op a
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db


# --- 3.a  similar customers by shared terminals ----------------------------
def query_a(db, M, min_shared=4, count_tol=2):
    """Customers N sharing >= min_shared terminals with M and tx count within
    count_tol. Returns names + shared count + both tx counts.
    Requires customer_terminals (build_derived.py)."""
    m = db.customer_terminals.find_one({"_id": M})
    if not m:
        return []
    name_m = (db.customers.find_one({"_id": M}) or {}).get("name")
    rows = list(db.customer_terminals.aggregate([
        {"$match": {"_id": {"$ne": M},
                    "txCount": {"$gte": m["txCount"] - count_tol,
                                "$lte": m["txCount"] + count_tol}}},   # cheap prune first
        {"$project": {"txCount": 1,
                      "shared": {"$size": {"$setIntersection":
                                           ["$terminals", m["terminals"]]}}}},
        {"$match": {"shared": {"$gte": min_shared}}},
        {"$lookup": {"from": "customers", "localField": "_id",
                     "foreignField": "_id", "as": "c"}},
        {"$project": {"_id": 0, "customerN": "$_id",
                      "nameN": {"$first": "$c.name"},
                      "sharedTerminals": "$shared", "txCountN": "$txCount"}},
    ], allowDiskUse=True))
    for r in rows:
        r["customerM"], r["nameM"], r["txCountM"] = M, name_m, m["txCount"]
    return rows


def query_a_all(db, **kw):
    """Run 3.a for every customer (used to stress the operation in benchmarks)."""
    out = []
    for c in db.customer_terminals.find({}, {"_id": 1}):
        out.extend(query_a(db, c["_id"], **kw))
    return out


# --- 3.b  quarterly per-terminal outliers -----------------------------------
def _median_stage(field):
    """$median accumulator (MongoDB >= 7.0)."""
    return {"$median": {"input": field, "method": "approximate"}}


def query_b(db, cur=(2024, 2), prev=(2024, 1), factor=1.3, set_flag=True):
    """Current-quarter tx more than `factor`x the previous-quarter median for
    their terminal -> 'potential outliers'. Optionally persists isOutlier
    (consumed by query e)."""
    db.terminal_prev_median.drop()
    db.transactions.aggregate([
        {"$match": {"year": prev[0], "quarter": prev[1]}},
        {"$group": {"_id": "$terminalId", "median": _median_stage("$amount")}},
        {"$merge": {"into": "terminal_prev_median"}}], allowDiskUse=True)

    pipeline = [
        {"$match": {"year": cur[0], "quarter": cur[1]}},
        {"$lookup": {"from": "terminal_prev_median", "localField": "terminalId",
                     "foreignField": "_id", "as": "m"}},
        {"$set": {"medPrev": {"$first": "$m.median"}}},
        {"$match": {"medPrev": {"$ne": None},
                    "$expr": {"$gt": ["$amount", {"$multiply": ["$medPrev", factor]}]}}},
    ]
    if set_flag:
        # persist the flag, then return the flagged docs
        db.transactions.aggregate(pipeline + [
            {"$set": {"isOutlier": True}},
            {"$merge": {"into": "transactions", "whenMatched": "merge"}}],
            allowDiskUse=True)
        return list(db.transactions.find(
            {"year": cur[0], "quarter": cur[1], "isOutlier": True},
            {"_id": 1, "terminalId": 1, "amount": 1}))
    return list(db.transactions.aggregate(pipeline + [
        {"$project": {"terminalId": 1, "amount": 1, "medPrev": 1}}], allowDiskUse=True))


# --- 3.c  co-customer network CC_k (k>=3) -----------------------------------
def query_c(db, u, k=3):
    """CC_k(u): customers reachable through shared-terminal paths of length k-1.
    maxDepth = k-2 (CC3 = 2 hops). Requires cocustomer_adj (build_derived.py)."""
    res = list(db.cocustomer_adj.aggregate([
        {"$match": {"_id": u}},
        {"$graphLookup": {
            "from": "cocustomer_adj", "startWith": "$neighbors",
            "connectFromField": "neighbors", "connectToField": "_id",
            "as": "net", "maxDepth": max(k - 2, 0), "depthField": "deg"}},
        {"$project": {"_id": 0, "cc": {"$setDifference": [
            {"$map": {"input": "$net", "in": "$$this._id"}}, [u]]}}}]))
    return res[0]["cc"] if res else []


# --- 3.e  day-of-week summary -----------------------------------------------
def query_e(db):
    """Per weekday: total tx and proportion flagged as outliers (from 3.b)."""
    return list(db.transactions.aggregate([
        {"$group": {"_id": "$dayOfWeek", "total": {"$sum": 1},
                    "outliers": {"$sum": {"$cond": ["$isOutlier", 1, 0]}}}},
        {"$project": {"_id": 0, "dayOfWeek": "$_id", "total": 1, "outliers": 1,
                      "outlierPct": {"$round": [{"$multiply": [
                          {"$divide": ["$outliers", {"$max": ["$total", 1]}]}, 100]}, 2]}}},
        {"$sort": {"dayOfWeek": 1}}]))


OPS = {
    "a": lambda db: query_a(db, db.customer_terminals.find_one()["_id"]),
    "a_all": query_a_all,
    "b": query_b,
    "c": lambda db: query_c(db, db.cocustomer_adj.find_one()["_id"], k=3),
    "e": query_e,
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--op", choices=list(OPS), default="e")
    args = ap.parse_args()
    res = OPS[args.op](get_db(args.dataset))
    print(res if not isinstance(res, list) else
          f"{len(res)} rows; sample: {res[:3]}")
