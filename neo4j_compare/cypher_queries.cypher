// Next-level cross-engine comparison: the same operations expressed in Cypher.
// Load customers/terminals/transactions as nodes + (:Customer)-[:AT]->(:Terminal)
// edges, then compare runtimes against the MongoDB implementations.

// --- 3.a  similar customers by shared terminals -----------------------------
MATCH (m:Customer)-[:TX]->(t:Terminal)<-[:TX]-(n:Customer)
WHERE m <> n
WITH m, n, count(DISTINCT t) AS shared,
     size((m)-[:TX]->()) AS txm, size((n)-[:TX]->()) AS txn
WHERE shared >= 4 AND abs(txm - txn) <= 2
RETURN m.name, n.name, shared, txm, txn;

// --- 3.c  co-customer network of degree 3 (2 hops) --------------------------
MATCH (u:Customer {id:$u})
MATCH p = (u)-[:TX]->(:Terminal)<-[:TX]-(:Customer)-[:TX]->(:Terminal)<-[:TX]-(y:Customer)
WHERE y <> u
RETURN DISTINCT y.id;

// Equivalent variable-length form over a projected SHARES relationship:
// MATCH (u:Customer {id:$u})-[:SHARES*1..2]-(y:Customer) RETURN DISTINCT y.id;
