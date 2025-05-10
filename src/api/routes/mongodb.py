from fastapi import APIRouter, Query
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
import sys
import logging
from collections import OrderedDict
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the analyze_papers_by_year_month_day function - use absolute import
from src.utils.analyze_papers_by_year_month_day import analyze_papers_by_year_month_day

router = APIRouter()

@router.get("/paper-stats")
def mongodb_paper_stats():
    # Try different connection strings in order of preference
    mongo_uri = os.getenv("MONGO_CONNECTION_STRING", None)
    if not mongo_uri:
        # For local development
        if os.path.exists('/etc/hosts'):  # Check if we're in a Unix-like system
            mongo_uri = "mongodb://localhost:27017/"
        else:  # Windows or other
            mongo_uri = "mongodb://localhost:27017/"
    
    # Log the connection string (without credentials)
    safe_uri = mongo_uri.replace("://", "://***:***@") if "@" in mongo_uri else mongo_uri
    logging.info(f"Connecting to MongoDB using: {safe_uri}")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        db = client["arxiv_papers"]
        papers_collection = db["papers"]
        papers_count = papers_collection.count_documents({})
        # Aggregate unique authors
        author_set = set()
        category_set = set()
        for doc in papers_collection.find({}, {"authors": 1, "categories": 1}):
            if "authors" in doc and isinstance(doc["authors"], list):
                author_set.update([a for a in doc["authors"] if isinstance(a, str)])
            if "categories" in doc and isinstance(doc["categories"], list):
                category_set.update([c for c in doc["categories"] if isinstance(c, str)])
        authors_count = len(author_set)
        categories_count = len(category_set)
        return {"papers": papers_count, "authors": authors_count, "categories": categories_count}
    except Exception as e:
        logger.error(f"MongoDB stats error: {str(e)}")
        # Return fallback values for UI compatibility
        return {"papers": 0, "authors": 0, "categories": 0, "error": str(e)}
    finally:
        client.close()

@router.get("/test-connection")
def test_mongodb_connection():
    # Try different connection strings in order of preference
    mongo_uri = os.getenv("MONGO_CONNECTION_STRING", None)
    if not mongo_uri:
        # For local development
        if os.path.exists('/etc/hosts'):  # Check if we're in a Unix-like system
            mongo_uri = "mongodb://localhost:27017/"
        else:  # Windows or other
            mongo_uri = "mongodb://localhost:27017/"
    
    # Log the connection string (without credentials)
    safe_uri = mongo_uri.replace("://", "://***:***@") if "@" in mongo_uri else mongo_uri
    logging.info(f"Connecting to MongoDB using: {safe_uri}")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ping')
        dbs = client.list_database_names()
        return {"status": "success", "message": "Connected to MongoDB", "databases": dbs}
    except ConnectionFailure as e:
        return {"status": "error", "message": str(e)}
    finally:
        client.close()


@router.get("/paper-analysis")
def get_papers_by_time(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    year_filter: Optional[int] = Query(None, description="Filter by specific year (e.g., 2023)"),
    category: Optional[str] = Query(None, description="Filter by paper category (e.g., cs.AI)")
) -> Dict[str, Any]:
    """
    Returns analysis of papers by year, month, and day.
    
    Args:
        start_date: Optional start date filter (format: YYYY-MM-DD)
        end_date: Optional end date filter (format: YYYY-MM-DD)
        year_filter: Optional year to filter results (e.g., 2023)
    
    Returns:
        Dictionary with yearly, monthly, and daily paper counts
    """
    # Try different connection strings in order of preference
    mongo_uri = os.getenv("MONGO_CONNECTION_STRING", None)
    if not mongo_uri:
        # For local development
        if os.path.exists('/etc/hosts'):  # Check if we're in a Unix-like system
            mongo_uri = "mongodb://localhost:27017/"
        else:  # Windows or other
            mongo_uri = "mongodb://localhost:27017/"
    
    # Log the connection string (without credentials)
    safe_uri = mongo_uri.replace("://", "://***:***@") if "@" in mongo_uri else mongo_uri
    logging.info(f"Connecting to MongoDB using: {safe_uri}")
    db_name = os.getenv("MONGO_DB_NAME", "arxiv_papers")
    
    try:
        # Call the analyze_papers_by_year_month_day function
        yearly_data, monthly_data, daily_data, total_papers, categories_list = analyze_papers_by_year_month_day(
            connection_string=mongo_uri,
            db_name=db_name,
            start_date=start_date,
            end_date=end_date,
            year_filter=year_filter,
            category=category
        )
        
        # Convert OrderedDict to dictionary for JSON serialization
        return {
            "yearly": {k: v for k, v in yearly_data.items()},
            "monthly": {k: v for k, v in monthly_data.items()},
            "daily": {k: v for k, v in daily_data.items()},
            "total_papers": total_papers,
            "categories": categories_list
        }
    except Exception as e:
        # Return empty datasets in case of error
        return {
            "yearly": {},
            "monthly": {},
            "daily": {},
            "total_papers": 0,
            "categories": [],
            "error": str(e)
        }
