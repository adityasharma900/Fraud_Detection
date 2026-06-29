"""
Smoke tests. Run against a live MongoDB after loading SAMPLE:
    python src/generate.py --sample && python src/load.py --dataset SAMPLE \
        && python src/build_derived.py --dataset SAMPLE \
        && python src/extend.py --dataset SAMPLE && pytest -q
Skipped automatically when no MongoDB is reachable.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from config import get_db
import queries


def _db():
    try:
        from pymongo import MongoClient
        db = get_db("SAMPLE")
        db.command("ping")
        if db.transactions.estimated_document_count() == 0:
            pytest.skip("SAMPLE not loaded")
        return db
    except Exception as e:
        pytest.skip(f"no MongoDB: {e}")


def test_query_a_shape():
    db = _db()
    m = db.customer_terminals.find_one()["_id"]
    for r in queries.query_a(db, m):
        assert r["sharedTerminals"] >= 4
        assert abs(r["txCountM"] - r["txCountN"]) <= 2


def test_query_e_seven_days():
    db = _db()
    res = queries.query_e(db)
    assert len(res) <= 7
    assert all(0 <= r["outlierPct"] <= 100 for r in res)


def test_query_c_excludes_self():
    db = _db()
    u = db.cocustomer_adj.find_one()["_id"]
    assert u not in queries.query_c(db, u, k=3)
