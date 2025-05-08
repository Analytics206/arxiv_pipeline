import os
import yaml
import logging
import pymongo
from pymongo import MongoClient
from datetime import datetime
from tqdm import tqdm

# Setup logging
from logger import setup_logger
logger = setup_logger("track_downloaded_pdfs")

def load_config():
    """Load configuration from default.yaml file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "default.yaml")
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

def ensure_collection(db, collection_name):
    """Ensure collection exists in MongoDB."""
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
        logger.info(f"Created new collection: {collection_name}")

def get_arxiv_id_from_filename(filename):
    """Extract arXiv ID from filename.
    Example: 2504.18538v1.pdf -> 2504.18538v1
    """
    if filename.endswith('.pdf'):
        return filename[:-4]  # Remove .pdf extension
    return filename

def scan_download_directory(pdf_dir, process_categories):
    """
    Scan the download directory for PDF files.
    Returns a dictionary mapping arXiv IDs to their categories.
    """
    downloaded_pdfs = {}
    
    # If process_categories is empty, scan all subdirectories
    if not process_categories:
        # Get all subdirectories in the PDF directory
        try:
            process_categories = [d for d in os.listdir(pdf_dir) 
                               if os.path.isdir(os.path.join(pdf_dir, d))]
        except FileNotFoundError:
            logger.error(f"PDF directory {pdf_dir} not found!")
            return downloaded_pdfs
    
    # Scan each category directory
    for category in process_categories:
        category_dir = os.path.join(pdf_dir, category)
        
        # Skip if category directory doesn't exist
        if not os.path.exists(category_dir):
            logger.warning(f"Category directory {category_dir} does not exist.")
            continue
        
        # Count PDFs in this category
        try:
            pdf_files = [f for f in os.listdir(category_dir) if f.endswith('.pdf')]
            for pdf_file in pdf_files:
                arxiv_id = get_arxiv_id_from_filename(pdf_file)
                downloaded_pdfs[arxiv_id] = category
        except Exception as e:
            logger.error(f"Error scanning directory {category_dir}: {e}")
    
    return downloaded_pdfs

def update_mongodb(mongo_client, db_name, collection_name, downloaded_pdfs):
    """
    Update MongoDB collection with downloaded PDFs information.
    - Adds entries for new downloads
    - Updates entries for existing downloads
    - Marks entries as not downloaded if PDF is no longer present
    """
    db = mongo_client[db_name]
    ensure_collection(db, collection_name)
    collection = db[collection_name]
    
    # Track statistics
    stats = {
        'added': 0,
        'updated': 0,
        'removed': 0,
        'unchanged': 0
    }
    
    # Use bulk operations for better performance
    bulk_operations = []
    max_bulk_size = 500  # Process in chunks to avoid memory issues
    timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Processing {len(downloaded_pdfs)} downloaded PDFs in MongoDB")
    
    # Get list of all downloaded PDFs in MongoDB
    existing_records = list(collection.find({}, {'_id': 0, 'arxiv_id': 1, 'category': 1, 'downloaded': 1}))
    existing_map = {doc['arxiv_id']: doc for doc in existing_records}
    
    # Process current downloads in batches
    download_items = list(downloaded_pdfs.items())
    total_batches = (len(download_items) + max_bulk_size - 1) // max_bulk_size
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * max_bulk_size
        end_idx = min((batch_idx + 1) * max_bulk_size, len(download_items))
        batch = download_items[start_idx:end_idx]
        
        bulk_operations = []
        for arxiv_id, category in batch:
            if arxiv_id in existing_map:
                record = existing_map[arxiv_id]
                # Update if category changed or marked as not downloaded previously
                if record.get('category') != category or record.get('downloaded') is not True:
                    bulk_operations.append(
                        pymongo.UpdateOne(
                            {'arxiv_id': arxiv_id},
                            {'$set': {
                                'category': category,
                                'downloaded': True,
                                'last_checked': timestamp
                            }}
                        )
                    )
                    stats['updated'] += 1
                else:
                    # Just update the last_checked timestamp
                    bulk_operations.append(
                        pymongo.UpdateOne(
                            {'arxiv_id': arxiv_id},
                            {'$set': {'last_checked': timestamp}}
                        )
                    )
                    stats['unchanged'] += 1
            else:
                # Add new record
                bulk_operations.append(
                    pymongo.InsertOne({
                        'arxiv_id': arxiv_id,
                        'category': category,
                        'downloaded': True,
                        'first_detected': timestamp,
                        'last_checked': timestamp
                    })
                )
                stats['added'] += 1
        
        # Execute bulk operations if any
        if bulk_operations:
            try:
                collection.bulk_write(bulk_operations, ordered=False)
                logger.info(f"Processed batch {batch_idx+1}/{total_batches} with {len(bulk_operations)} operations")
            except Exception as e:
                logger.error(f"Error processing batch {batch_idx+1}: {e}")
    
    # Mark PDFs as not downloaded if they're no longer present (in batches)
    to_mark_as_removed = []
    for record in existing_records:
        arxiv_id = record.get('arxiv_id')
        if arxiv_id not in downloaded_pdfs and record.get('downloaded', False):
            to_mark_as_removed.append(arxiv_id)
    
    # Process removals in batches
    total_remove_batches = (len(to_mark_as_removed) + max_bulk_size - 1) // max_bulk_size
    logger.info(f"Processing {len(to_mark_as_removed)} PDFs to mark as removed in {total_remove_batches} batches")
    
    for batch_idx in range(total_remove_batches):
        if not to_mark_as_removed:  # Skip if nothing to process
            break
            
        start_idx = batch_idx * max_bulk_size
        end_idx = min((batch_idx + 1) * max_bulk_size, len(to_mark_as_removed))
        batch = to_mark_as_removed[start_idx:end_idx]
        
        if batch:  # Only proceed if batch has items
            try:
                # Mark all in batch as not downloaded
                collection.update_many(
                    {'arxiv_id': {'$in': batch}},
                    {'$set': {
                        'downloaded': False,
                        'last_checked': timestamp
                    }}
                )
                stats['removed'] += len(batch)
                logger.info(f"Processed removal batch {batch_idx+1}/{total_remove_batches} with {len(batch)} operations")
            except Exception as e:
                logger.error(f"Error processing removal batch {batch_idx+1}: {e}")
    
    return stats

def main():
    """Main function to track downloaded PDFs."""
    # Load configuration
    config = load_config()
    
    # Get settings from config
    mongo_uri = os.getenv("MONGO_URI", config['mongo']['connection_string_local'])
    db_name = config['mongo']['db_name']
    pdf_dir = config['pdf_storage']['directory']
    process_categories = config['pdf_storage'].get('process_categories', [])
    
    # Set MongoDB connection timeout values
    mongo_client_options = {
        'serverSelectionTimeoutMS': 10000,  # Reduce server selection timeout
        'connectTimeoutMS': 10000,         # Reduce connection timeout
        'socketTimeoutMS': 30000           # Socket timeout for operations
    }
    
    logger.info(f"PDF Directory: {pdf_dir}")
    if process_categories:
        logger.info(f"Processing categories: {', '.join(process_categories)}")
    else:
        logger.info("Processing all available categories")
    
    try:
        # Connect to MongoDB with timeout options
        client = MongoClient(mongo_uri, **mongo_client_options)
        # Test connection by executing a simple command
        client.admin.command('ping')
        logger.info(f"Connected to MongoDB at {mongo_uri}")
        
        # Scan download directory
        downloaded_pdfs = scan_download_directory(pdf_dir, process_categories)
        logger.info(f"Found {len(downloaded_pdfs)} downloaded PDFs across all categories")
        
        # Update MongoDB
        stats = update_mongodb(client, db_name, 'downloaded_pdfs', downloaded_pdfs)
        
        # Print summary
        logger.info("PDF tracking complete!")
        logger.info(f"Added: {stats['added']} new records")
        logger.info(f"Updated: {stats['updated']} existing records")
        logger.info(f"Removed: {stats['removed']} PDFs no longer present")
        logger.info(f"Unchanged: {stats['unchanged']} PDFs")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Close MongoDB connection
        if 'client' in locals():
            client.close()
            logger.info("MongoDB connection closed")

if __name__ == "__main__":
    main()
