import os
import yaml
from pymongo import MongoClient
import re

# Setup logging
from logger import setup_logger
logger = setup_logger("check_pdf_urls")

def load_config():
    """Load configuration from default.yaml file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "default.yaml")
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

def check_pdf_urls():
    """Check MongoDB for papers with /pdf/ in the pdf_url and analyze downloaded files."""
    # Load configuration
    config = load_config()
    
    # Get MongoDB connection settings
    mongo_uri = os.getenv("MONGO_URI", config['mongo']['connection_string_local'])
    db_name = config['mongo']['db_name']
    pdf_dir = config['pdf_storage']['directory']
    
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    papers_collection = db["papers"]
    downloaded_pdfs_collection = db["downloaded_pdfs"]
    
    # Query papers with /pdf/ in the pdf_url
    pdf_pattern_query = {"pdf_url": {"$regex": "/pdf/", "$options": "i"}}
    papers_with_pdf_pattern = list(papers_collection.find(pdf_pattern_query, {"_id": 0, "pdf_url": 1, "title": 1, "categories": 1}))
    
    logger.info(f"Found {len(papers_with_pdf_pattern)} papers with '/pdf/' in the pdf_url")
    
    # Check if any of these papers have been downloaded
    # by extracting arxiv IDs and checking against downloaded_pdfs collection
    if papers_with_pdf_pattern:
        downloaded_with_pattern = []
        not_downloaded_with_pattern = []
        
        # Get all downloaded paper IDs
        downloaded_papers = list(downloaded_pdfs_collection.find({"downloaded": True}, {"arxiv_id": 1, "_id": 0}))
        downloaded_ids = {doc["arxiv_id"] for doc in downloaded_papers}
        
        for paper in papers_with_pdf_pattern:
            pdf_url = paper.get("pdf_url", "")
            
            # Extract arXiv ID from the pdf_url
            arxiv_id = pdf_url.rstrip("/").split("/")[-1] if pdf_url else ""
            
            if arxiv_id in downloaded_ids:
                downloaded_with_pattern.append({
                    "arxiv_id": arxiv_id,
                    "pdf_url": pdf_url,
                    "title": paper.get("title", "Unknown"),
                    "categories": paper.get("categories", [])
                })
            else:
                not_downloaded_with_pattern.append({
                    "arxiv_id": arxiv_id,
                    "pdf_url": pdf_url,
                    "title": paper.get("title", "Unknown"),
                    "categories": paper.get("categories", [])
                })
        
        logger.info(f"Of these, {len(downloaded_with_pattern)} have been downloaded and {len(not_downloaded_with_pattern)} have not")
        
        # Print some example papers that have been downloaded
        if downloaded_with_pattern:
            logger.info("\nExamples of downloaded papers with '/pdf/' in URL:")
            for i, paper in enumerate(downloaded_with_pattern[:5]):  # Show first 5 examples
                logger.info(f"Paper {i+1}:")
                logger.info(f"  ArXiv ID: {paper['arxiv_id']}")
                logger.info(f"  URL: {paper['pdf_url']}")
                logger.info(f"  Title: {paper['title']}")
                logger.info(f"  Categories: {', '.join(paper['categories'])}")
        
        # Check the physical files on disk
        file_exists_count = 0
        file_missing_count = 0
        
        logger.info("\nChecking if files exist on disk...")
        
        for paper in downloaded_with_pattern:
            arxiv_id = paper["arxiv_id"]
            categories = paper.get("categories", [])
            
            # For each category, check if the file exists in that directory
            file_found = False
            for category in categories:
                category_dir = os.path.join(pdf_dir, category)
                if os.path.exists(category_dir):
                    filepath = os.path.join(category_dir, f"{arxiv_id}.pdf")
                    if os.path.exists(filepath):
                        file_found = True
                        file_exists_count += 1
                        break
            
            if not file_found:
                file_missing_count += 1
        
        logger.info(f"Of {len(downloaded_with_pattern)} papers marked as downloaded:")
        logger.info(f"  - {file_exists_count} files exist on disk")
        logger.info(f"  - {file_missing_count} files are missing from disk")
        
    client.close()
    logger.info("Analysis complete")

if __name__ == "__main__":
    check_pdf_urls()
