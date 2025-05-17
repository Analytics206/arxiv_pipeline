#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Query script to get paper counts by topic from MongoDB collection "paper_top2vec_topics".
This helps verify that the Top2Vec processing pipeline is working correctly.
"""

import argparse
import yaml
import os
from typing import Dict, Any
import pandas as pd
from pymongo import MongoClient
import logging
from tabulate import tabulate
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration settings from a YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def is_docker() -> bool:
    """Detect if running inside a Docker container."""
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        return False

def get_mongo_uri(config: Dict[str, Any]) -> str:
    """Get the appropriate MongoDB URI based on environment and configuration."""
    # First check environment variable
    mongo_uri = os.environ.get('MONGO_URI')
    if mongo_uri:
        return mongo_uri
        
    # Then use config based on environment
    if is_docker():
        return config['top2vec']['mongo']['connection_string']
    return config['top2vec']['mongo']['connection_string_local']

def query_topics(config: Dict[str, Any]) -> None:
    """Query the top2vec topics collection and display statistics."""
    try:
        # Connect to MongoDB
        mongo_uri = get_mongo_uri(config)
        client = MongoClient(mongo_uri)
        db = client[config['top2vec']['mongo']['database']]
        topics_collection = db[config['top2vec']['mongo']['topics_collection']]
        
        # Get total count of documents in the collection
        total_docs = topics_collection.count_documents({})
        logger.info(f"Total documents in {config['top2vec']['mongo']['topics_collection']}: {total_docs}")
        
        if total_docs == 0:
            logger.warning("No documents found in the collection.")
            return
        
        # Query to count papers by topic_id
        pipeline = [
            {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        topic_counts = list(topics_collection.aggregate(pipeline))
        
        # Format results for display
        rows = []
        topic_words_dict = defaultdict(list)
        
        # Get sample words for each topic (if available)
        for topic_id in [item["_id"] for item in topic_counts]:
            sample = topics_collection.find_one({"topic_id": topic_id})
            if sample and "topic_words" in sample and sample["topic_words"]:
                # Get top words for this topic (limited to first 5 for readability)
                topic_words_dict[topic_id] = sample["topic_words"][:5]
        
        # Generate the table data
        for item in topic_counts:
            topic_id = item["_id"]
            count = item["count"]
            
            # Format words for display
            words = topic_words_dict.get(topic_id, [])
            words_str = ", ".join(words) if words else "No words available"
            
            # Add a row to our table
            rows.append([topic_id, count, words_str])
        
        # Display the results as a table
        headers = ["Topic ID", "Paper Count", "Top Words"]
        print("\nTopic Distribution:")
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Calculate some statistics
        topic_distribution = pd.DataFrame(topic_counts)
        if not topic_distribution.empty:
            print("\nSummary Statistics:")
            print(f"Total Topics: {len(topic_counts)}")
            print(f"Average Papers per Topic: {topic_distribution['count'].mean():.2f}")
            print(f"Min Papers per Topic: {topic_distribution['count'].min()}")
            print(f"Max Papers per Topic: {topic_distribution['count'].max()}")
        
    except Exception as e:
        logger.error(f"Error querying topics: {str(e)}")

def main() -> None:
    """Main entry point for the query script."""
    parser = argparse.ArgumentParser(description='Query Top2Vec topics in MongoDB')
    parser.add_argument('--config', default='config/default.yaml', help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    logger.info('Querying Top2Vec topics from MongoDB')
    query_topics(config)

if __name__ == "__main__":
    main()
