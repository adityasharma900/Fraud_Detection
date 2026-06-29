"""Central configuration: dataset parameters and the Mongo connection helper."""
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
SEED = 42
START_DATE = "2024-01-01"
RADIUS = 30                      # geographic reachability radius

# Dataset definitions. `nb_days` is the lever used to hit the size targets;
# 1000 customers x ~2 tx/day -> ~2000 tx/day, so days ~= target_tx / 2000.
# Calibrate: generate, read meta.json size, bump nb_days if below target.
DATASETS = {
    "D1": dict(n_customers=1000, n_terminals=200, nb_days=250,  target_mb=50),
    "D2": dict(n_customers=1000, n_terminals=200, nb_days=500,  target_mb=100),
    "D3": dict(n_customers=1000, n_terminals=200, nb_days=1000, target_mb=200),
}

# Tiny config used by the offline pandas oracle / smoke tests.
SAMPLE = dict(n_customers=60, n_terminals=25, nb_days=200, target_mb=0)

PAYMENT_METHODS = ["credit_card", "mobile_payment", "paypal"]


def get_db(dataset):
    """Return the database handle for a given dataset name."""
    from pymongo import MongoClient  # lazy: generation/oracle need no MongoDB
    return MongoClient(MONGO_URI)[f"fraud_{dataset}"]


def data_dir(dataset):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "data", dataset)
