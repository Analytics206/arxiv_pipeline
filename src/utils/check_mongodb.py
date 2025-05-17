from pymongo import MongoClient

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/config')
    db = client['arxiv_papers']
    
    # Count total papers
    total_papers = db.papers.count_documents({})
    print(f"Total papers in MongoDB: {total_papers}")
    
    # Count AI/ML papers
    ai_ml_papers = db.papers.count_documents({
        'categories': {'$in': ['cs.AI', 'cs.LG']}
    })
    print(f"AI/ML papers: {ai_ml_papers}")
    
    # Check date range
    date_papers = db.papers.count_documents({
        'categories': {'$in': ['cs.AI', 'cs.LG']},
        'published': {
            '$gte': '2023-01-01',
            '$lte': '2025-05-20'
        }
    })
    print(f"AI/ML papers in date range: {date_papers}")
    
    # Show sample paper
    sample = db.papers.find_one({
        'categories': {'$in': ['cs.AI', 'cs.LG']}
    })
    if sample:
        print("\nSample paper:")
        print(f"ID: {sample.get('_id')}")
        print(f"Title: {sample.get('title')}")
        print(f"Categories: {sample.get('categories')}")
        print(f"Published: {sample.get('published')}")
        print(f"Has summary: {'summary' in sample}")

if __name__ == "__main__":
    main()
