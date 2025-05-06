from fastapi import APIRouter
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

router = APIRouter()

@router.get("/paper-stats")
def mongodb_paper_stats():
    mongo_uri = os.getenv("MONGO_CONNECTION_STRING", "mongodb://mongodb:27017/")
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
        return {"papers": 0, "authors": 0, "categories": 0, "error": str(e)}
    finally:
        client.close()

@router.get("/test-connection")
def test_mongodb_connection():
    mongo_uri = os.getenv("MONGO_CONNECTION_STRING", "mongodb://mongodb:27017/")
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
