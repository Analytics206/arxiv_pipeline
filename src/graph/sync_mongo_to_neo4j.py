import logging
from pymongo import MongoClient
from src.graph.neo4j_sync import Neo4jSync
from configparser import ConfigParser
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(path="config/default.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    mongo_conf = config["mongo"]
    neo4j_conf = config["neo4j"]

    # Connect to MongoDB
    mongo_client = MongoClient(mongo_conf["connection_string"])
    db = mongo_client[mongo_conf["db_name"]]
    papers = list(db.papers.find({}))

    logger.info(f"Loaded {len(papers)} papers from MongoDB.")

    # Connect to Neo4j and sync
    neo4j_sync = Neo4jSync(
        uri=neo4j_conf["url"],
        user=neo4j_conf["user"],
        password=neo4j_conf["password"]
    )
    neo4j_sync.sync_papers(papers)
    neo4j_sync.close()
    logger.info("Sync to Neo4j complete.")

if __name__ == "__main__":
    main()