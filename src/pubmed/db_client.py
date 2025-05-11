# db_client.py
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, COLLECTION_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def article_exists(pmid):
    return collection.find_one({"pmid": pmid}) is not None

def save_article(data):
    if isinstance(data, dict):
        collection.insert_one(data)

def save_articles(data_list):
    if data_list:
        collection.insert_many(data_list)

def get_article(pmid):
    return collection.find_one({"pmid": pmid})
