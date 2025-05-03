import os
import requests
from pymongo import MongoClient
from tqdm import tqdm
# should be renamed this imports pds into MongoDB

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = "arxiv_papers"
COLLECTION_NAME = "papers"
PDF_DIR = r"E:\AI Research"

print("MONGO_URI:", MONGO_URI)

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

def main():
    ensure_dir(PDF_DIR)
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    papers = db[COLLECTION_NAME].find({"pdf_url": {"$exists": True, "$ne": ""}})

    for paper in tqdm(papers, desc="Downloading PDFs"):
        pdf_url = paper.get("pdf_url")
        if not pdf_url:
            continue
        filename = get_pdf_filename(paper)
        filepath = os.path.join(PDF_DIR, filename)
        if os.path.exists(filepath):
            continue  # Skip if already downloaded
        download_pdf(pdf_url, filepath)

if __name__ == "__main__":
    main()