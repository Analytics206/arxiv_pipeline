from pymongo import MongoClient
import yaml
from collections import Counter
from typing import Dict, Any

def load_config(config_path: str = 'config/default.yaml') -> Dict[str, Any]:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    # Load config
    config = load_config()
    
    # Connect to MongoDB
    client = MongoClient(config['bertopic']['mongo']['connection_string_local'])
    db = client[config['bertopic']['mongo']['db_name']]
    topics_collection = db[config['bertopic']['mongo']['topics_collection']]
    
    # Get total count
    total_papers = topics_collection.count_documents({})
    print(f"\nTotal papers with topics: {total_papers}")
    
    # Aggregate topics
    pipeline = [
        {
            '$group': {
                '_id': {
                    'topic_id': '$topic_id',
                    'topic_name': '$topic_name'
                },
                'count': {'$sum': 1},
                'avg_probability': {'$avg': '$probability'}
            }
        },
        {'$sort': {'count': -1}}
    ]
    
    results = list(topics_collection.aggregate(pipeline))
    
    print("\nTopic Distribution:")
    print("-" * 80)
    print(f"{'Topic ID':<10} {'Count':<8} {'Avg Prob':<10} Topic Name")
    print("-" * 80)
    
    for result in results:
        topic_id = result['_id']['topic_id']
        topic_name = result['_id']['topic_name']
        count = result['count']
        avg_prob = result['avg_probability']
        print(f"{topic_id:<10} {count:<8} {avg_prob:.4f}    {topic_name}")

if __name__ == "__main__":
    main()
