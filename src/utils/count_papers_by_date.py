"""
Count ArXiv papers by publication date from MongoDB.
This utility script queries the MongoDB papers collection and 
displays counts of papers grouped by their publication dates.
"""

import os
import sys
import logging
from datetime import datetime
from collections import OrderedDict
import pymongo
from pymongo import MongoClient

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the MongoStorage class from the project
from src.storage.mongo import MongoStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def count_papers_by_published_date(connection_string=None, db_name="arxiv_papers"):
    """
    Query MongoDB and count papers grouped by published date.
    
    Args:
        connection_string: MongoDB connection URI (if None, uses MONGO_URI env var or default)
        db_name: MongoDB database name
        
    Returns:
        Ordered dictionary of publication dates and paper counts
    """
    # Use environment variable or default connection string
    if connection_string is None:
        connection_string = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    
    logger.info(f"Connecting to MongoDB at {connection_string}")
    
    try:
        # Connect to MongoDB using the project's MongoStorage class
        with MongoStorage(connection_string=connection_string, db_name=db_name) as mongo:
            # Query to group papers by publication date and count them
            # Since published is stored as an ISO string like '2025-04-25T17:59:59Z'
            # We need to extract just the date part (first 10 characters)
            pipeline = [
                {"$addFields": {"publishedDate": {"$substr": ["$published", 0, 10]}}},
                {"$group": {"_id": "$publishedDate", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}  # Sort by date ascending
            ]
            
            # Execute the aggregation pipeline
            logger.info("Executing aggregation query...")
            result = mongo.papers.aggregate(pipeline)
            
            # Convert results to ordered dictionary
            counts = OrderedDict()
            for doc in result:
                counts[doc["_id"]] = doc["count"]
            
            logger.info(f"Found papers published on {len(counts)} different dates")
            return counts
            
    except Exception as e:
        logger.error(f"Error querying MongoDB: {str(e)}")
        return OrderedDict()

def display_results(counts):
    """
    Display paper counts in a formatted way.
    
    Args:
        counts: Ordered dictionary of dates and counts
    """
    if not counts:
        print("No results found or error occurred.")
        return
        
    print("\n📊 ArXiv Papers by Publication Date 📊")
    print("-" * 40)
    print(f"{'Date':<12} | {'Count':>8} | {'Percentage':>12}")
    print("-" * 40)
    
    total = sum(counts.values())
    
    # Display most recent dates last (reverse the items)
    for date, count in reversed(list(counts.items())[-20:]):  # Show only the 20 most recent dates
        percentage = (count / total) * 100
        print(f"{date:<12} | {count:>8,d} | {percentage:>11.2f}%")
    
    print("-" * 40)
    print(f"Total Papers: {total:,d}")

def main():
    """Main entry point for the script."""
    try:
        # Get MongoDB connection string from environment variable or use default
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.environ.get("MONGO_DB", "arxiv_papers")
        
        logger.info(f"Using database: {db_name}")
        
        # Get counts of papers by publication date
        counts = count_papers_by_published_date(mongo_uri, db_name)
        
        # Display results
        display_results(counts)
        
        # Also display monthly aggregation
        if counts:
            print("\n📅 Monthly Summary 📅")
            print("-" * 40)
            print(f"{'Month':<10} | {'Count':>8} | {'Percentage':>12}")
            print("-" * 40)
            
            # Group by month
            monthly = OrderedDict()
            for date, count in counts.items():
                if date and len(date) >= 7:  # Ensure date is valid
                    month = date[:7]  # Extract YYYY-MM
                    monthly[month] = monthly.get(month, 0) + count
            
            total = sum(monthly.values())
            
            # Display the 12 most recent months
            for month, count in reversed(list(monthly.items())[-12:]):
                percentage = (count / total) * 100
                print(f"{month:<10} | {count:>8,d} | {percentage:>11.2f}%")
                
            print("-" * 40)
            print(f"Total Papers: {total:,d}")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
