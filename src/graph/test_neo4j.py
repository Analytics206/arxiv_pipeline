from neo4j import GraphDatabase

uri = "bolt://neo4j:7687"
user = "neo4j"
password = "password"

driver = GraphDatabase.driver(uri, auth=(user, password))
try:
    with driver.session() as session:
        result = session.run("RETURN 1 AS test")
        print("Neo4j connection successful:", result.single()["test"])
except Exception as e:
    print("Neo4j connection failed:", e)
finally:
    driver.close()