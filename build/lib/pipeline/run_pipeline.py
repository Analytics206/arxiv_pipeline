import logging
import argparse
import yaml
from datetime import datetime
from typing import Dict, Any

from src.ingestion.fetch import ArxivClient
from src.storage.mongo import MongoStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def run_ingestion_pipeline(config: Dict[str, Any]):
    """Run the arXiv ingestion pipeline."""
    # Initialize components
    arxiv_client = ArxivClient(
        max_results=config['arxiv']['max_results'],
        sort_by=config['arxiv']['sort_by'],
        sort_order=config['arxiv']['sort_order']
    )
    
    mongo_storage = MongoStorage(
        connection_string=config['mongo']['connection_string'],
        db_name=config['mongo']['db_name']
    )
    
    # Process each category
    for category in config['arxiv']['categories']:
        logger.info(f"Processing category: {category}")
        
        # Parameters for pagination
        start = 0
        max_iterations = config['arxiv'].get('max_iterations', 10)
        total_papers = 0
        
        # Fetch and store papers with pagination
        for iteration in range(max_iterations):
            logger.info(f"Fetching batch {iteration+1}/{max_iterations}, start={start}")
            
            # Fetch papers
            papers = arxiv_client.fetch_papers(
                category=category,
                search_query=config['arxiv'].get('search_query'),
                start=start
            )
            
            if not papers:
                logger.info("No more papers to fetch")
                break
                
            # Store papers
            stats = mongo_storage.store_papers(papers)
            total_papers += len(papers)
            
            # Update start for next iteration
            start += len(papers)
            
            # Log progress
            logger.info(f"Progress: {total_papers} papers processed so far")
            
            # Optional rate limiting
            if config['arxiv'].get('rate_limit_seconds'):
                import time
                time.sleep(config['arxiv']['rate_limit_seconds'])
    
    logger.info(f"Ingestion pipeline completed. Total papers processed: {total_papers}")

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Run arXiv ingestion pipeline')
    parser.add_argument('--config', default='config/default.yaml', help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Run pipeline
    logger.info("Starting arXiv ingestion pipeline")
    start_time = datetime.now()
    
    try:
        run_ingestion_pipeline(config)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        
    finally:
        execution_time = datetime.now() - start_time
        logger.info(f"Pipeline execution completed in {execution_time}")

if __name__ == "__main__":
    main()