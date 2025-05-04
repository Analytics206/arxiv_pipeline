import os
import requests
import yaml
from pymongo import MongoClient
from tqdm import tqdm

# Load configuration from file
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "default.yaml")
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

config = load_config()

# Get settings from config
MONGO_URI = os.getenv("MONGO_URI", config['mongo']['connection_string'])
DB_NAME = config['mongo']['db_name']
COLLECTION_NAME = "papers"
PDF_DIR = config['pdf_storage']['directory']
PAPERS_PER_CATEGORY = config['pdf_storage'].get('papers_per_category', 0)  # 0 means unlimited
PROCESS_CATEGORIES = config['pdf_storage'].get('process_categories', [])  # Categories to process

# Get date filter settings
DATE_FILTER_ENABLED = config['pdf_storage'].get('download_date_filter', {}).get('enabled', False)
START_DATE = config['pdf_storage'].get('download_date_filter', {}).get('start_date', None)
END_DATE = config['pdf_storage'].get('download_date_filter', {}).get('end_date', None)
SORT_BY_DATE = config['pdf_storage'].get('download_date_filter', {}).get('sort_by_date', False)

print("MONGO_URI:", MONGO_URI)
print("PDF_DIR:", PDF_DIR)
print("PAPERS_PER_CATEGORY:", "Unlimited" if PAPERS_PER_CATEGORY == 0 else PAPERS_PER_CATEGORY)
if PROCESS_CATEGORIES:
    print(f"PROCESS CATEGORIES: {', '.join(PROCESS_CATEGORIES)}")
else:
    print("PROCESS CATEGORIES: All categories")
if DATE_FILTER_ENABLED:
    print(f"DATE FILTER: {START_DATE} to {END_DATE}")
else:
    print("DATE FILTER: Disabled")

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_pdf_filename(paper):
    # Extract arXiv ID from the pdf_url or id field
    pdf_url = paper.get("pdf_url", "")
    # Example: http://arxiv.org/pdf/2504.18538v1
    arxiv_id = pdf_url.rstrip("/").split("/")[-1]
    return f"{arxiv_id}.pdf"

def download_pdf(url, filepath):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def filter_papers_by_date(papers_cursor, start_date=None, end_date=None):
    """Filter papers by published date (ISO format: YYYY-MM-DD)."""
    from datetime import datetime
    
    filtered_papers = []
    for paper in papers_cursor:
        # Skip papers without published date
        if 'published' not in paper:
            continue
            
        # Parse paper date (format: YYYY-MM-DDT12:00:00Z)
        try:
            paper_date = datetime.fromisoformat(paper['published'][:10])
        except (ValueError, TypeError, IndexError):
            continue  # Skip papers with invalid date format
        
        # Apply date filters
        if start_date and end_date:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            if start <= paper_date <= end:
                filtered_papers.append(paper)
        elif start_date:
            start = datetime.fromisoformat(start_date)
            if start <= paper_date:
                filtered_papers.append(paper)
        elif end_date:
            end = datetime.fromisoformat(end_date)
            if paper_date <= end:
                filtered_papers.append(paper)
        else:
            filtered_papers.append(paper)
    
    return filtered_papers

def sort_papers_by_date(papers, ascending=False):
    """Sort papers by published date."""
    from datetime import datetime
    
    def get_date(paper):
        try:
            return datetime.fromisoformat(paper.get('published', '1970-01-01')[:10])
        except (ValueError, TypeError, IndexError):
            return datetime.fromisoformat('1970-01-01')
    
    return sorted(papers, key=get_date, reverse=not ascending)

def main():
    ensure_dir(PDF_DIR)
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Query MongoDB for papers with PDF URLs
    query = {"pdf_url": {"$exists": True, "$ne": ""}}
    
    # Add category filter if process_categories is specified
    if PROCESS_CATEGORIES:
        query["categories"] = {"$in": PROCESS_CATEGORIES}
    sort_order = None
    
    # Handle date sorting if enabled
    if SORT_BY_DATE:
        # Sort by published date in descending order (newest first)
        sort_order = [("published", -1)]
    
    # Fetch papers from MongoDB
    if sort_order:
        papers_cursor = db[COLLECTION_NAME].find(query).sort(sort_order)
    else:
        papers_cursor = db[COLLECTION_NAME].find(query)
    
    # Filter by date if enabled
    if DATE_FILTER_ENABLED and (START_DATE or END_DATE):
        print(f"Filtering papers by date: {START_DATE or 'any'} to {END_DATE or 'any'}")
        papers = filter_papers_by_date(papers_cursor, START_DATE, END_DATE)
        
        # Re-sort after filtering if needed
        if SORT_BY_DATE:
            papers = sort_papers_by_date(papers)
        
        # Count unique categories
        categories_found = set()
        for paper in papers:
            for category in paper.get('categories', []):
                categories_found.add(category)
            
        print(f"Found {len(papers)} papers matching date criteria across {len(categories_found)} unique categories")
    else:
        # Convert cursor to list for consistent processing
        papers = list(papers_cursor)
    
    # Track paper count per category
    category_counts = {}
    total_papers = len(papers)
    
    # Process all papers by category
    for paper in tqdm(papers, desc=f"Downloading PDFs ({total_papers} papers)"):
        pdf_url = paper.get("pdf_url")
        if not pdf_url:
            continue
            
        # Get primary category - use the first one if multiple exist
        categories = paper.get("categories", [])
        if not categories:
            category_dir = "uncategorized"  # Default if no category is found
        else:
            # Use the first category as the primary one
            category_dir = categories[0]
            
        # Create category directory if it doesn't exist
        category_path = os.path.join(PDF_DIR, category_dir)
        ensure_dir(category_path)
        
        # Save the PDF to the category subdirectory
        filename = get_pdf_filename(paper)
        filepath = os.path.join(category_path, filename)
        
        # Check if we've hit the limit for this category
        if PAPERS_PER_CATEGORY > 0:  # Only check if we have a limit
            # Initialize counter if this is a new category
            if category_dir not in category_counts:
                category_counts[category_dir] = 0
                
            # Skip if we've reached the limit for this category
            if category_counts[category_dir] >= PAPERS_PER_CATEGORY:
                continue
        
        # Skip if already downloaded - this check comes AFTER the limit check
        # so we don't count already downloaded PDFs toward the limit
        if os.path.exists(filepath):
            continue
            
        # Download the PDF
        success = download_pdf(pdf_url, filepath)
        
        # Increment counter if download was successful - only counts NEW downloads
        if success and PAPERS_PER_CATEGORY > 0:
            category_counts[category_dir] += 1
            
    # Print summary of papers downloaded per category
    if category_counts:
        print("\nPapers downloaded per category:")
        for category, count in category_counts.items():
            print(f"  {category}: {count}" + (" (reached limit)" if PAPERS_PER_CATEGORY > 0 and count >= PAPERS_PER_CATEGORY else ""))
    else:
        print("\nNo new papers were downloaded.")

if __name__ == "__main__":
    main()