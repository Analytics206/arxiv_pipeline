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

def filter_papers_by_date(papers, start_date, end_date):
    """Filter papers by published date (ISO format: YYYY-MM-DD)."""
    from datetime import datetime
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return [
        paper for paper in papers
        if 'published' in paper and start <= datetime.fromisoformat(paper['published'][:10]) <= end
    ]

def run_ingestion_pipeline(config: Dict[str, Any]):
    """Run the arXiv ingestion pipeline."""
    # Initialize components
    arxiv_client = ArxivClient(
        max_results=config['arxiv']['max_results'],
        sort_by=config['arxiv']['sort_by'],
        sort_order=config['arxiv']['sort_order']
    )
    
    # Use environment variable if available, otherwise use config
    import os
    mongo_uri = os.environ.get('MONGO_URI', config['mongo']['connection_string'])
    
    mongo_storage = MongoStorage(
        connection_string=mongo_uri,
        db_name=config['mongo']['db_name']
    )
    
    logger.info(f"Using MongoDB connection: {mongo_uri}")
    
    
    # Process each category
    for category in config['arxiv']['categories']:
        logger.info(f"Processing category: {category}")
        
        # Parameters for pagination
        start = 0
        max_iterations = config['arxiv'].get('max_iterations', 2)
        total_papers = 0
        empty_batches = 0
        max_results = config['arxiv']['max_results']
        
        # Fetch and store papers with pagination
        for iteration in range(max_iterations):
            logger.info(f"Fetching batch {iteration+1}/{max_iterations}, start={start}")
            
            # Fetch papers
            papers = arxiv_client.fetch_papers(
                category=category,
                search_query=config['arxiv'].get('search_query'),
                start=start
            )
            logger.info(f"Fetched {len(papers)} papers from arXiv before filtering.")

            # Filter by date if configured
            start_date = config['arxiv'].get('start_date')
            end_date = config['arxiv'].get('end_date')
            if start_date and end_date:
                before_filter = len(papers)
                papers = filter_papers_by_date(papers, start_date, end_date)
                logger.info(f"{len(papers)} papers remain after date filtering ({before_filter - len(papers)} filtered out).")
                logger.info(f"Date range filter: {start_date} to {end_date}")

            if not papers:
                empty_batches += 1
                logger.info(f"Empty batch {empty_batches}, continuing...")
            else:
                empty_batches = 0  # Reset if we get papers
                # Store papers
                stats = mongo_storage.store_papers(papers)
                total_papers += len(papers)

            # Always increment start by max_results to avoid infinite loop
            start += max_results

            if empty_batches >= 20:
                logger.info("No more papers to fetch after 5 empty batches")
                break

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
    parser.add_argument('--runs', type=int, default=1, help='Number of times to run the pipeline')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Run pipeline the specified number of times
    for run in range(args.runs):
        logger.info(f"Starting arXiv ingestion pipeline (run {run+1}/{args.runs})")
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
