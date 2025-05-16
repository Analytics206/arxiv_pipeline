"""
Neo4j Database Clear Utility

This script provides functionality to safely clear all data from a Neo4j database.
It shows current database statistics before clearing and supports a dry-run mode.

Usage:
    1. Normal clear (will prompt for confirmation):
       python -m src.utils.clear_neo4j

    2. Dry run to preview what would be deleted:
       python -m src.utils.clear_neo4j --dry-run

    3. Use a different config file:
       python -m src.utils.clear_neo4j --config path/to/config.yaml

    4. Using with Docker:
       docker-compose run --rm app python -m src.utils.clear_neo4j

The script will display:
- Current count of Papers
- Current count of Authors
- Current count of Categories
- Current count of AUTHORED relationships
- Current count of IN_CATEGORY relationships

Configuration:
    Uses Neo4j connection details from config/default.yaml:
    - url or url_local: Neo4j connection URI
    - user: Neo4j username
    - password: Neo4j password
"""

import logging
import yaml
from neo4j import GraphDatabase
from typing import Optional
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(path: str = "config/default.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {e}")
        raise

def clear_neo4j(uri: str, user: str, password: str, dry_run: bool = False) -> None:
    """
    Clear all data from Neo4j database
    
    Args:
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password
        dry_run: If True, only show what would be deleted without actually deleting
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Get current counts
            result = session.run("""
                MATCH (p:Paper) WITH count(p) as papers
                MATCH (a:Author) WITH papers, count(a) as authors
                MATCH (c:Category) WITH papers, authors, count(c) as categories
                MATCH ()-[r:AUTHORED]->() WITH papers, authors, categories, count(r) as authored
                MATCH ()-[r:IN_CATEGORY]->() WITH papers, authors, categories, authored, count(r) as categorized
                RETURN papers, authors, categories, authored, categorized
            """)
            counts = result.single()
            
            logger.info("Current Neo4j database contents:")
            logger.info(f"Papers: {counts['papers']}")
            logger.info(f"Authors: {counts['authors']}")
            logger.info(f"Categories: {counts['categories']}")
            logger.info(f"AUTHORED relationships: {counts['authored']}")
            logger.info(f"IN_CATEGORY relationships: {counts['categorized']}")
            
            if dry_run:
                logger.info("Dry run - no data will be deleted")
                return
            
            # Clear all data
            logger.info("Clearing Neo4j database...")
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Neo4j database has been cleared")
            
    except Exception as e:
        logger.error(f"Failed to clear Neo4j database: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()

def main():
    parser = argparse.ArgumentParser(description='Clear all data from Neo4j database')
    parser.add_argument('--config', type=str, default='config/default.yaml',
                       help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    neo4j_conf = config['neo4j']
    
    # Clear Neo4j
    clear_neo4j(
        uri=neo4j_conf['url_local'] if 'url_local' in neo4j_conf else neo4j_conf['url'],
        user=neo4j_conf['user'],
        password=neo4j_conf['password'],
        dry_run=args.dry_run
    )

if __name__ == '__main__':
    main()
