"""
Skeleton harness for the MongoDB-vs-Neo4j comparison on query (c).
Requires a running Neo4j and `pip install neo4j`. Documents the methodology;
fill in the connection details to run the head-to-head.
"""
import time


def time_neo4j_cc3(driver, u):
    cypher = ("MATCH (u:Customer {id:$u})-[:SHARES*1..2]-(y:Customer) "
              "RETURN DISTINCT y.id")
    t0 = time.perf_counter()
    with driver.session() as s:
        res = [r["y.id"] for r in s.run(cypher, u=u)]
    return res, time.perf_counter() - t0


if __name__ == "__main__":
    print("Provide a Neo4j driver and call time_neo4j_cc3(driver, u). "
          "Compare against src/queries.query_c on the same dataset.")
