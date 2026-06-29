"""$jsonSchema validators (next-level: enforce structure in a schemaless store)."""

CUSTOMER_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["_id", "name", "location", "availableTerminals"],
    "properties": {
        "_id": {"bsonType": "int"},
        "name": {"bsonType": "string"},
        "meanAmount": {"bsonType": ["double", "int"], "minimum": 0},
        "availableTerminals": {"bsonType": "array", "items": {"bsonType": "int"}},
    }}}

TRANSACTION_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["_id", "customerId", "terminalId", "datetime", "amount", "fraud"],
    "properties": {
        "_id": {"bsonType": "int"},
        "customerId": {"bsonType": "int"},
        "terminalId": {"bsonType": "int"},
        "amount": {"bsonType": ["double", "int"], "minimum": 0},
        "fraud": {"enum": [0, 1]},
        "satisfaction": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 5},
        "paymentMethod": {"enum": ["credit_card", "mobile_payment", "paypal", None]},
    }}}


def apply_validators(db):
    """Attach validators to existing collections via collMod (idempotent)."""
    for coll, validator in (("customers", CUSTOMER_VALIDATOR),
                            ("transactions", TRANSACTION_VALIDATOR)):
        db.command({"collMod": coll, "validator": validator,
                    "validationLevel": "moderate"})
