"""
Examine the structure of paper documents in MongoDB.
"""

import os
import sys
import json
from datetime import datetime
import pymongo
from bson import ObjectId

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the MongoStorage class from the project
from src.storage.mongo import MongoStorage

def inspect_paper_schema():
    """Examine the structure of a paper document in MongoDB."""
    # Use environment variable or default connection string
    connection_string = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGO_DB", "arxiv_papers")
    
    print(f"Connecting to MongoDB at {connection_string}, database: {db_name}")
    
    # Connect to MongoDB using the project's MongoStorage class
    storage = MongoStorage(connection_string=connection_string, db_name=db_name)
    
    try:
        # Get a single paper document
        paper = storage.papers.find_one()
        
        if not paper:
            print("No papers found in the collection.")
            return
        
        # Print publication field information
        print("\n=== Published Field Analysis ===")
        published_field = paper.get('published')
        print(f"Published field type: {type(published_field)}")
        print(f"Published field value: {published_field}")
        
        # Print sample of the document structure
        print("\n=== Sample Document Structure ===")
        # Convert ObjectId and datetime objects to strings for JSON serialization
        paper_dict = {k: (str(v) if isinstance(v, (datetime, ObjectId)) else v) 
                      for k, v in paper.items()}
        print(json.dumps(paper_dict, indent=2, default=str))
        
        # Try different grouping approaches
        print("\n=== Testing Publication Date Aggregation ===")
        
        # Count total papers
        total_count = storage.papers.count_documents({})
        print(f"Total papers in collection: {total_count}")
        
        # Try simple grouping if published is a string
        if isinstance(published_field, str):
            print("Attempting string-based aggregation...")
            pipeline = [
                {"$group": {"_id": "$published", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
                {"$limit": 5}  # Just show first 5 results
            ]
            results = list(storage.papers.aggregate(pipeline))
            print(f"Found {len(results)} distinct published values")
            for result in results:
                print(f"  {result['_id']}: {result['count']} papers")
        
    finally:
        storage.close()

if __name__ == "__main__":
    inspect_paper_schema()
