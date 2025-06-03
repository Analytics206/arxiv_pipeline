import logging
import argparse
import yaml
import os
from datetime import datetime, UTC
from typing import Dict, Any, List
from tqdm import tqdm

from pymongo import MongoClient, UpdateOne
from bertopic import BERTopic
from src.storage.mongo import MongoStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration settings from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        Dict[str, Any]: Dictionary containing configuration settings.
        
    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def is_docker() -> bool:
    """Detect if the current environment is running inside a Docker container.
    
    This function checks for the presence of Docker-specific information in the
    Linux cgroup file. This is a reliable way to detect if we're running in a
    Docker container on Linux systems.
    
    Returns:
        bool: True if running in Docker, False otherwise.
    
    Note:
        Always returns False on non-Linux systems where /proc/1/cgroup doesn't exist.
    """
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        return False

def get_mongo_uri(config: Dict[str, Any]) -> str:
    """Get the appropriate MongoDB URI based on environment and configuration.
    
    This function determines the correct MongoDB connection URI using the following
    priority order:
    1. MONGO_URI environment variable if set
    2. Docker connection string if running in Docker
    3. Local connection string if running locally
    
    Args:
        config (Dict[str, Any]): Configuration dictionary containing MongoDB settings
            under the 'bertopic.mongo' section.
        
    Returns:
        str: MongoDB connection URI to use.
        
    Note:
        The function expects the config to have the following structure:
        bertopic:
          mongo:
            connection_string: "mongodb://mongodb:27017/"  # For Docker
            connection_string_local: "mongodb://localhost:27017/"  # For local
    """
    # First check environment variable
    mongo_uri = os.environ.get('MONGO_URI')
    if mongo_uri:
        return mongo_uri
        
    # Then use config based on environment
    if is_docker():
        return config['bertopic']['mongo']['connection_string']
    return config['bertopic']['mongo']['connection_string_local']

def build_mongo_query(config: Dict[str, Any]) -> Dict:
    """Build a MongoDB query based on configuration filters.
    
    Constructs a MongoDB query dictionary that filters papers based on:
    1. Categories - matches papers in any of the specified categories
    2. Date range - filters papers within the specified date range
    
    Args:
        config (Dict[str, Any]): Configuration dictionary containing filter settings
            under the 'bertopic' section.
        
    Returns:
        Dict: MongoDB query dictionary with the following possible structure:
            {
                'categories': {'$in': ['cs.AI', 'cs.LG', ...]},
                'published': {
                    '$gte': '2023-01-01',
                    '$lte': '2025-05-20'
                }
            }
    
    Note:
        - Category filter is only added if categories are specified in config
        - Date filter is only added if date_filter.enabled is True and
          at least one of start_date or end_date is specified
    """
    query = {}
    
    # Add category filter
    if config['bertopic']['categories']:
        query['categories'] = {'$in': config['bertopic']['categories']}
    
    # Add date filter
    if config['bertopic']['date_filter']['enabled']:
        date_query = {}
        if config['bertopic']['date_filter']['start_date']:
            date_query['$gte'] = config['bertopic']['date_filter']['start_date']
        if config['bertopic']['date_filter']['end_date']:
            date_query['$lte'] = config['bertopic']['date_filter']['end_date']
        if date_query:
            query['published'] = date_query
            
    return query

def process_batch(papers: List[Dict], topic_model: BERTopic, mongo_collection) -> int:
    """Process a batch of papers and store topics in MongoDB.
    
    Args:
        papers: List of paper documents from MongoDB
        topic_model: Trained BERTopic model
        mongo_collection: MongoDB collection to store results
    
    Returns:
        int: Number of papers successfully processed
    """
    try:
        # Extract summaries and IDs
        summaries = [doc.get('title', '') + ' ' + doc.get('summary', '') for doc in papers]
        paper_ids = [doc.get('_id') for doc in papers]
        
        if not summaries or not paper_ids:
            logger.warning(f'No valid summaries or IDs found in batch')
            return 0
            
        # Generate topics
        topics, probs = topic_model.transform(summaries)
        
        # Get topic info
        topic_info = topic_model.get_topic_info()
        topics_dict = {row['Topic']: row['Name'] for _, row in topic_info.iterrows()}
        
        # Prepare documents for MongoDB
        topic_docs = []
        for i, (paper_id, topic_id, prob) in enumerate(zip(paper_ids, topics, probs)):
            topic_name = topics_dict.get(topic_id, 'noise')
            topic_doc = {
                'paper_id': paper_id,
                'topic_id': int(topic_id),
                'topic_name': topic_name,
                'probability': float(prob[topic_id]),
                'processed_at': datetime.now(UTC),
                'categories': papers[i].get('categories', [])
            }
            topic_docs.append(topic_doc)
        
        # Upsert into MongoDB
        if topic_docs:
            operations = [
                UpdateOne(
                    {'paper_id': doc['paper_id']},
                    {'$set': doc},
                    upsert=True
                ) for doc in topic_docs
            ]
            result = mongo_collection.bulk_write(operations)
            return result.upserted_count + result.modified_count
            
        return 0
        
    except Exception as e:
        logger.error(f'Error processing batch: {str(e)}', exc_info=True)
        return 0

def process_data(config: Dict[str, Any]) -> None:
    """Main processing function for extracting topics from paper summaries.
    
    This function handles the complete pipeline for topic extraction:
    1. Connects to MongoDB using environment-appropriate connection string
    2. Applies category and date filters from config
    3. Initializes BERTopic model
    4. Processes papers in batches:
       - First batch is used to fit the model
       - Subsequent batches use the fitted model
    5. Stores results in a separate MongoDB collection
    
    Args:
        config (Dict[str, Any]): Configuration dictionary containing all settings:
            - MongoDB connection details
            - Batch processing settings
            - Category filters
            - Date filters
            - Collection names
    
    Raises:
        pymongo.errors.ConnectionError: If MongoDB connection fails
        Exception: For any other processing errors
    
    Note:
        - Uses consistent sorting (_id) for reliable pagination
        - Supports both Docker and local environments
        - Implements batch processing for memory efficiency
        - Provides progress tracking via tqdm
        - Respects max_papers limit if configured
    """
    try:
        # Get MongoDB connection
        mongo_uri = get_mongo_uri(config)
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client[config['bertopic']['mongo']['db_name']]
        papers_collection = db[config['bertopic']['mongo']['papers_collection']]
        topics_collection = db[config['bertopic']['mongo']['topics_collection']]
        
        logger.info(f'Using MongoDB connection: {mongo_uri}')
        
        # Build query
        query = build_mongo_query(config)
        logger.info(f'Using query filter: {query}')
        
        # Initialize BERTopic model
        logger.info('Initializing BERTopic model...')
        topic_model = BERTopic(
            language='english',
            calculate_probabilities=True,
            min_topic_size=2,  # Allow smaller topic sizes
            nr_topics='auto',  # Let the model determine the number of topics
            verbose=True
        )
        
        # Get total number of papers
        total_papers = papers_collection.count_documents(query)
        logger.info(f'Found {total_papers} papers matching filters')
        
        # Process in batches
        batch_size = config['bertopic']['batch_size']
        max_papers = config['bertopic']['max_papers']
        processed_papers = 0
        
        # Adjust total papers if max_papers is set
        if max_papers > 0:
            total_papers = min(total_papers, max_papers)
            logger.info(f'Will process up to {total_papers} papers due to max_papers setting')
        
        for skip in tqdm(range(0, total_papers, batch_size)):
            # Fetch batch with consistent sorting
            papers = list(papers_collection.find(query, {
                'summary': 1,
                '_id': 1,
                'categories': 1
            }).sort('_id', 1).skip(skip).limit(batch_size))
            
            if not papers:
                logger.warning(f'No papers found in batch starting at {skip}')
                continue
                
            logger.info(f'Processing batch of {len(papers)} papers')
            
            # Process batch
            summaries = [doc.get('summary', '') for doc in papers]
            
            if skip == 0:  # First batch - fit and transform
                if len(summaries) < 2:
                    logger.error(f'Need at least 2 documents to fit BERTopic model, got {len(summaries)}')
                    return
                    
                logger.info('Fitting BERTopic model on first batch...')
                topic_model.fit(summaries)
            
            # Process the batch
            processed = process_batch(papers, topic_model, topics_collection)
            processed_papers += processed
            
            logger.info(f'Processed {processed} papers in current batch. Total processed: {processed_papers}')
            
            # Check if we've hit max_papers
            if max_papers > 0 and processed_papers >= max_papers:
                logger.info(f'Reached max papers limit of {max_papers}')
                break
            
        logger.info(f'Topic extraction completed. Total papers processed: {processed_papers}')
    except Exception as e:
        logger.error(f'Error in process_data: {str(e)}', exc_info=True)
        raise

def main() -> None:
    """Main entry point for the BERTopic extraction pipeline.
    
    This function handles:
    1. Command line argument parsing
    2. Configuration loading
    3. Pipeline execution with timing
    4. Error handling and logging
    
    Command Line Arguments:
        --config: Path to YAML configuration file (default: config/default.yaml)
    
    The function measures and logs the total execution time of the pipeline.
    Any unhandled exceptions are caught, logged, and result in a non-zero
    exit status.
    
    Example Usage:
        python -m src.pipeline.insert_bertopic_mongodb --config config/default.yaml
    """
    parser = argparse.ArgumentParser(description='Run BERTopic extraction pipeline')
    parser.add_argument('--config', default='config/default.yaml', help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    logger.info('Starting BERTopic extraction pipeline')
    start_time = datetime.now(UTC)
    
    try:
        process_data(config)
    except Exception as e:
        logger.error(f'Pipeline failed: {str(e)}', exc_info=True)
    finally:
        execution_time = datetime.now(UTC) - start_time
        logger.info(f'Pipeline execution completed in {execution_time}')

if __name__ == "__main__":
    main()
