import os
import yaml
import datetime
import pymongo
from pymongo import MongoClient
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from tqdm import tqdm
import torch

# Load configuration from file
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "default.yaml")
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

config = load_config()

# Get settings from config
PAPER_SUMMARIES_ENABLED = config.get('paper_summaries', {}).get('enabled', False)
QDRANT_URL = config['qdrant']['url']
QDRANT_COLLECTION = config.get('paper_summaries', {}).get('qdrant', {}).get('collection_name', 'papers_summary')
# The actual vector size depends on the model - all-MiniLM-L6-v2 produces 384-dimension vectors
VECTOR_SIZE = 384  # Hardcoded to match the actual dimension of the model

# Handle path differences between Docker container and local environment
if os.environ.get('DOCKER_ENV', '').lower() == 'true' or os.path.exists('/app'):
    print("Running in Docker environment")
    # In Docker, use service names instead of localhost
    MONGO_URI = config['mongo']['connection_string']
    QDRANT_URL = config['qdrant']['url']
else:
    print("Running in local environment")
    # For local execution use localhost
    MONGO_URI = config['mongo'].get('connection_string_local', "mongodb://localhost:27017/")
    QDRANT_URL = config['qdrant'].get('url_local', "http://localhost:6333")

# Get MongoDB settings
MONGO_DB = config['mongo']['db_name']
PROCESS_CATEGORIES = config.get('paper_summaries', {}).get('process_categories', [])
MAX_PAPERS_PER_CATEGORY = config.get('paper_summaries', {}).get('papers_per_category', 0)  # 0 means unlimited

# Get date filter settings
DATE_FILTER_ENABLED = config.get('paper_summaries', {}).get('date_filter', {}).get('enabled', False)
START_DATE = config.get('paper_summaries', {}).get('date_filter', {}).get('start_date')
END_DATE = config.get('paper_summaries', {}).get('date_filter', {}).get('end_date')
SORT_BY_DATE = config.get('paper_summaries', {}).get('date_filter', {}).get('sort_by_date', True)

# Tracking settings
TRACKING_ENABLED = config.get('paper_summaries', {}).get('tracking', {}).get('enabled', False)
TRACKING_COLLECTION = config.get('paper_summaries', {}).get('tracking', {}).get('collection_name', 'summary_processed_papers')
SYNC_WITH_QDRANT = config.get('paper_summaries', {}).get('tracking', {}).get('sync_with_qdrant', False)

# Initialize MongoDB client for data retrieval and tracking
mongo_client = None
papers_collection = None
tracking_collection = None

# Configure GPU settings if available
GPU_ENABLED = config.get('qdrant', {}).get('gpu_enabled', False)
GPU_DEVICE = config.get('qdrant', {}).get('gpu_device', 0)

if GPU_ENABLED and torch.cuda.is_available():
    device = f"cuda:{GPU_DEVICE}"
    print(f"Using GPU device: {device}")
else:
    device = "cpu"
    print("Using CPU for embeddings")

# Initialize MongoDB client
try:
    mongo_client = MongoClient(MONGO_URI)
    papers_collection = mongo_client[MONGO_DB]['papers']
    print(f"Connected to MongoDB: {MONGO_URI}, Database: {MONGO_DB}")
    
    if TRACKING_ENABLED:
        tracking_collection = mongo_client[MONGO_DB][TRACKING_COLLECTION]
        print(f"MongoDB tracking enabled using collection: {TRACKING_COLLECTION}")
        
        # Create indexes if they don't exist
        tracking_collection.create_index("paper_id", unique=True)
        tracking_collection.create_index("category")
        tracking_collection.create_index("processed_date")
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
    raise

def is_paper_processed(paper_id, category=None):
    """Check if a paper has already been processed and stored in Qdrant."""
    if not TRACKING_ENABLED or tracking_collection is None:
        return False  # If tracking disabled, process all papers
    
    # Check if paper exists in tracking collection
    query = {"paper_id": paper_id}
    if category:
        query["category"] = category
        
    result = tracking_collection.find_one(query)
    return result is not None

def mark_paper_as_processed(paper_id, category, summary_length=0):
    """Mark a paper as processed in the tracking database."""
    if not TRACKING_ENABLED or tracking_collection is None:
        return
        
    # Generate metadata for tracking
    tracking_data = {
        "paper_id": paper_id,
        "category": category,
        "processed_date": datetime.datetime.now(),
        "summary_length": summary_length
    }
    
    # Upsert to tracking collection
    tracking_collection.update_one(
        {"paper_id": paper_id},
        {"$set": tracking_data},
        upsert=True
    )
    
    print(f"Marked paper {paper_id} as processed in tracking database")

def sync_qdrant_with_tracking():
    """Synchronize MongoDB tracking with actual Qdrant contents."""
    if not TRACKING_ENABLED or tracking_collection is None:
        print("Tracking not enabled, skipping synchronization")
        return set()
        
    print("Synchronizing tracking database with Qdrant collection...")
    
    try:
        # Connect to Qdrant
        client = QdrantClient(url=QDRANT_URL)
        
        # Get collection info to check if it exists
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if QDRANT_COLLECTION not in collection_names:
            print(f"Qdrant collection {QDRANT_COLLECTION} does not exist, creating it")
            # Create the collection with the specified vector size
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config={
                    "default": {
                        "size": VECTOR_SIZE,
                        "distance": "Cosine"
                    }
                }
            )
            print(f"Created new collection {QDRANT_COLLECTION}")
            return set()
            
        # Get all records from Qdrant with batching for large collections
        print("Retrieving papers from Qdrant collection...")
        qdrant_paper_ids = set()
        offset = None
        batch_size = 1000
        
        try:
            while True:
                batch, next_offset = client.scroll(
                    collection_name=QDRANT_COLLECTION,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                if not batch:
                    break
                    
                # Extract paper IDs from the batch
                for record in batch:
                    paper_id = record.payload.get("paper_id")
                    if paper_id:
                        qdrant_paper_ids.add(paper_id)
                
                # If there's no next offset, we've reached the end
                if next_offset is None:
                    break
                    
                offset = next_offset
        except Exception as e:
            print(f"Error retrieving papers from Qdrant: {str(e)}")
            # Continue with what we have
                
        print(f"Found {len(qdrant_paper_ids)} papers in Qdrant collection")
        
        # If we have papers in Qdrant, update tracking to match
        if qdrant_paper_ids:
            # Get all records from tracking collection
            tracking_records = list(tracking_collection.find({}, {"paper_id": 1}))
            tracking_paper_ids = {record["paper_id"] for record in tracking_records}
            
            print(f"Found {len(tracking_paper_ids)} papers in tracking collection")
            
            # Find papers in tracking but not in Qdrant (to be removed from tracking)
            to_remove = tracking_paper_ids - qdrant_paper_ids
            if to_remove:
                print(f"Removing {len(to_remove)} papers from tracking that are not in Qdrant")
                tracking_collection.delete_many({"paper_id": {"$in": list(to_remove)}})
                
            # Find papers in Qdrant but not in tracking (to be added to tracking)
            to_add = qdrant_paper_ids - tracking_paper_ids
            if to_add:
                print(f"Adding {len(to_add)} papers to tracking that are in Qdrant")
                bulk_operations = []
                
                for paper_id in to_add:
                    # Find the paper in MongoDB to get its category
                    paper = papers_collection.find_one({"id": paper_id}, {"categories": 1, "summary": 1, "published": 1})
                    
                    if paper and "categories" in paper:
                        # Use the first category as the primary category
                        category = paper["categories"][0] if isinstance(paper["categories"], list) and paper["categories"] else "unknown"
                        summary_length = len(paper.get("summary", ""))
                        
                        # Create tracking document
                        tracking_data = {
                            "paper_id": paper_id,
                            "category": category,
                            "processed_date": datetime.datetime.now(),
                            "summary_length": summary_length,
                            "published": paper.get("published")
                        }
                        
                        # Add to bulk operations
                        bulk_operations.append(
                            pymongo.UpdateOne(
                                {"paper_id": paper_id},
                                {"$set": tracking_data},
                                upsert=True
                            )
                        )
                    else:
                        # If paper not found in MongoDB, still track it but with minimal info
                        tracking_data = {
                            "paper_id": paper_id,
                            "category": "unknown",
                            "processed_date": datetime.datetime.now(),
                            "summary_length": 0
                        }
                        
                        # Add to bulk operations
                        bulk_operations.append(
                            pymongo.UpdateOne(
                                {"paper_id": paper_id},
                                {"$set": tracking_data},
                                upsert=True
                            )
                        )
                
                # Execute bulk operations if there are any
                if bulk_operations:
                    tracking_collection.bulk_write(bulk_operations, ordered=False)
        else:
            # If no papers in Qdrant, leave tracking alone - we'll be adding papers soon
            print("No papers found in Qdrant collection, maintaining tracking collection unchanged")
                    
        print("Synchronization completed")
        return qdrant_paper_ids
    except Exception as e:
        print(f"Error during synchronization: {str(e)}")
        return set()

def create_query_filter():
    """Create a MongoDB query filter based on configuration settings."""
    query_filter = {}
    
    # Filter for papers that have a summary field
    query_filter["summary"] = {"$exists": True, "$ne": None, "$ne": ""}
    
    # Add category filter if specified
    if PROCESS_CATEGORIES:
        query_filter["categories"] = {"$in": PROCESS_CATEGORIES}
        
    # Add date filter if enabled
    if DATE_FILTER_ENABLED:
        date_filter = {}
        if START_DATE:
            date_filter["$gte"] = START_DATE
        if END_DATE:
            date_filter["$lte"] = END_DATE
        if date_filter:
            query_filter["published"] = date_filter
            
    return query_filter

def process_papers():
    """Process papers from MongoDB and store their summaries in Qdrant."""
    if not PAPER_SUMMARIES_ENABLED:
        print("Paper summaries processing is disabled in configuration")
        return {"processed": 0}
        
    print(f"Processing papers for summary vectorization to Qdrant collection: {QDRANT_COLLECTION}")
    
    # Create Qdrant client first
    try:
        client = QdrantClient(url=QDRANT_URL)
    except Exception as e:
        print(f"Error connecting to Qdrant: {str(e)}")
        return {"processed": 0}
    
    # Function to reset the Qdrant collection
    def reset_qdrant_collection(client):
        try:
            # Check if collection exists
            collections = client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            # If collection exists, delete it
            if QDRANT_COLLECTION in collection_names:
                print(f"Deleting existing Qdrant collection {QDRANT_COLLECTION}")
                client.delete_collection(collection_name=QDRANT_COLLECTION)
                print(f"Collection {QDRANT_COLLECTION} deleted")
            
            # Create collection with correct vector dimensions
            print(f"Creating Qdrant collection {QDRANT_COLLECTION} with vector size {VECTOR_SIZE}")
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config={
                    "default": {
                        "size": VECTOR_SIZE,
                        "distance": "Cosine"
                    }
                }
            )
            print(f"Created new collection {QDRANT_COLLECTION}")
            return True
        except Exception as e:
            print(f"Error resetting Qdrant collection: {str(e)}")
            return False
    
    # Reset the Qdrant collection to ensure correct vector dimensions
    if not reset_qdrant_collection(client):
        print("Failed to reset Qdrant collection, aborting process")
        return {"processed": 0}
    
    # Step 1: Get existing papers from tracking collection
    existing_paper_ids = set()
    if TRACKING_ENABLED:
        print("Step 1: Getting papers from tracking collection...")
        tracking_records = list(tracking_collection.find({}, {"paper_id": 1}))
        existing_paper_ids = {record["paper_id"] for record in tracking_records}
        print(f"Found {len(existing_paper_ids)} papers in tracking collection")
    
    # Step 2: Create MongoDB query filter for papers to process
    query_filter = create_query_filter()
    print(f"Step 2: Using query filter: {query_filter}")
    
    # Step 3: Add exclusion for already processed papers
    if existing_paper_ids and TRACKING_ENABLED:
        # Exclude papers that are already in tracking
        query_filter["id"] = {"$nin": list(existing_paper_ids)}
        print(f"Added exclusion filter for {len(existing_paper_ids)} already processed papers")
    
    # Get count of papers matching filter
    total_papers = papers_collection.count_documents(query_filter)
    print(f"Found {total_papers} new papers to process")
    
    if total_papers == 0:
        print("No new papers found to process")
        return {"processed": 0}
    
    # Apply papers_per_category limit if set
    limit = MAX_PAPERS_PER_CATEGORY if MAX_PAPERS_PER_CATEGORY > 0 else total_papers
    print(f"Processing up to {limit} papers")
    
    # Set up sort order
    sort_order = [("published", -1)] if SORT_BY_DATE else None
    
    # Step 4: Get unprocessed papers from MongoDB
    print("Step 3: Retrieving unprocessed papers from MongoDB...")
    cursor = papers_collection.find(
        query_filter,
        {"id": 1, "title": 1, "summary": 1, "categories": 1, "published": 1}
    ).sort(sort_order).limit(limit)
    
    # Convert cursor to list for progress tracking
    papers = list(cursor)
    print(f"Retrieved {len(papers)} unprocessed papers for processing")
    
    if not papers:
        print("No papers to process after filtering")
        return {"processed": 0}
    
    # Step 5: Initialize embeddings model
    model_name = config['embedding']['model_name']
    print(f"Step 4: Initializing embedding model: {model_name}")
    
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True}
    )
    
    # Step 6: Process papers in batches and store in Qdrant
    print("Step 5: Processing papers and storing in Qdrant...")
    batch_size = config['embedding']['batch_size']
    papers_processed = 0
    bulk_tracking_operations = []
    
    for i in range(0, len(papers), batch_size):
        batch = papers[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{len(papers)//batch_size + 1} ({len(batch)} papers)")
        
        # Prepare documents for vectorization
        documents = []
        metadata_list = []
        batch_paper_ids = []
        batch_categories = []
        batch_summary_lengths = []
        
        for paper in batch:
            summary = paper.get("summary", "")
            if not summary:
                continue
                
            # Get primary category (first in list)
            category = paper["categories"][0] if isinstance(paper["categories"], list) and paper["categories"] else "unknown"
            
            # Prepare metadata
            metadata = {
                "paper_id": paper["id"],
                "title": paper.get("title", ""),
                "category": category,
                "published": paper.get("published", ""),
                "summary_length": len(summary),
                "summary": summary  # Store the actual summary in the payload
            }
            
            documents.append(summary)
            metadata_list.append(metadata)
            batch_paper_ids.append(paper["id"])
            batch_categories.append(category)
            batch_summary_lengths.append(len(summary))
        
        if not documents:
            print("No valid documents in batch, skipping")
            continue
        
        try:
            # Use direct Qdrant client instead of using langchain's from_texts method
            # This gives us more control over the process
            ids = []
            vectors = []
            payloads = []
            
            # Generate embeddings for all documents
            embedded_documents = embeddings.embed_documents(documents)
            
            # Prepare data for Qdrant batch insertion
            for idx, (vector, metadata) in enumerate(zip(embedded_documents, metadata_list)):
                # Generate a deterministic ID based on paper_id
                point_id = int(hash(metadata["paper_id"]) % (10**18))  # Ensure it's a positive integer within Qdrant limits
                ids.append(point_id)
                vectors.append(vector)
                payloads.append(metadata)
            
            # Insert into Qdrant using batch operation
            operation_info = client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    {
                        "id": ids[i],
                        "vector": {"default": vectors[i]},
                        "payload": payloads[i]
                    } for i in range(len(ids))
                ]
            )
            
            print(f"Upserted {len(ids)} documents into Qdrant")
            
            # Step 7: Prepare tracking operations for bulk update
            if TRACKING_ENABLED:
                for idx, paper_id in enumerate(batch_paper_ids):
                    tracking_data = {
                        "paper_id": paper_id,
                        "category": batch_categories[idx],
                        "processed_date": datetime.datetime.now(),
                        "summary_length": batch_summary_lengths[idx],
                        "qdrant_id": str(ids[idx]) if idx < len(ids) else None
                    }
                    
                    bulk_tracking_operations.append(
                        pymongo.UpdateOne(
                            {"paper_id": paper_id},
                            {"$set": tracking_data},
                            upsert=True
                        )
                    )
                    
            papers_processed += len(documents)
            print(f"Successfully processed batch, total papers processed: {papers_processed}")
            
        except Exception as e:
            print(f"Error processing batch: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Step 8: Execute bulk tracking updates
    if TRACKING_ENABLED and bulk_tracking_operations:
        print(f"Step 6: Updating tracking collection with {len(bulk_tracking_operations)} papers...")
        try:
            tracking_collection.bulk_write(bulk_tracking_operations, ordered=False)
            print("Successfully updated tracking collection")
        except Exception as e:
            print(f"Error updating tracking collection: {str(e)}")
    
    # If we've added papers to Qdrant, update the tracking by syncing only if we have SYNC_WITH_QDRANT enabled
    if SYNC_WITH_QDRANT and papers_processed > 0:
        print("Syncing tracking database with Qdrant after adding new papers...")
        sync_qdrant_with_tracking()
    
    print(f"Total papers processed: {papers_processed}")
    return {"processed": papers_processed}

if __name__ == "__main__":
    if not PAPER_SUMMARIES_ENABLED:
        print("Paper summaries processing is disabled in configuration")
    else:
        # Process papers and store summaries in Qdrant
        results = process_papers()
        print(f"Processing completed. Processed {results['processed']} papers.")
