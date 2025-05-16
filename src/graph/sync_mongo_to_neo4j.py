import logging
import time
import yaml
from datetime import datetime
from pymongo import MongoClient
from src.graph.neo4j_sync import Neo4jSync
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(path="config/default.yaml"):
    """Load configuration from YAML file"""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {e}")
        raise

def main():
    start_time = time.time()
    config = load_config()
    mongo_conf = config["mongo"]
    neo4j_conf = config["neo4j"]
    
    # Set batch size for processing papers
    batch_size = 1000
    
    try:
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        mongo_client = MongoClient(mongo_conf["connection_string"])
        db = mongo_client[mongo_conf["db_name"]]
        
        # Get total count of papers (for progress tracking)
        total_count = db.papers.count_documents({})
        logger.info(f"Found {total_count} papers in MongoDB.")
        
        # Connect to Neo4j
        logger.info("Connecting to Neo4j...")
        neo4j_sync = Neo4jSync(
            uri=neo4j_conf["url"],
            user=neo4j_conf["user"],
            password=neo4j_conf["password"]
        )
        
        # Clear existing Neo4j data (optional - uncomment if needed)
        # logger.info("Clearing existing Neo4j data...")
        # neo4j_sync.clear_database()
        
        # Process papers in batches
        processed_count = 0
        successful_count = 0
        error_count = 0
        
        # Setup progress bar
        progress = tqdm(total=total_count, desc="Syncing papers to Neo4j")
        
        # Get the current timestamp for tracking
        sync_timestamp = datetime.now().isoformat()
        
        # Process in batches
        for skip in range(0, total_count, batch_size):
            try:
                # Fetch a batch of papers
                papers_batch = list(db.papers.find({}).skip(skip).limit(batch_size))
                batch_count = len(papers_batch)
                
                if batch_count == 0:
                    break
                    
                logger.info(f"Processing batch of {batch_count} papers (total processed: {processed_count})")
                
                # Sync batch to Neo4j
                batch_success, batch_errors = neo4j_sync.sync_papers_batch(papers_batch, sync_timestamp)
                
                # Update counters
                successful_count += batch_success
                error_count += batch_errors
                processed_count += batch_count
                
                # Update progress bar
                progress.update(batch_count)
                
            except Exception as e:
                logger.error(f"Error processing batch starting at index {skip}: {e}")
                error_count += 1
        
        progress.close()
        
        # Log final statistics
        elapsed_time = time.time() - start_time
        logger.info(f"Sync to Neo4j complete in {elapsed_time:.2f} seconds.")
        logger.info(f"Total papers processed: {processed_count}")
        logger.info(f"Successfully synced: {successful_count}")
        logger.info(f"Errors encountered: {error_count}")
        
        # Close connections
        neo4j_sync.close()
        mongo_client.close()
        
    except Exception as e:
        logger.error(f"Fatal error in sync process: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()