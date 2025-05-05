import os
import yaml
import hashlib
import datetime
from pymongo import MongoClient
from qdrant_client import QdrantClient
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.schema.document import Document
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from PIL import Image
import fitz  # PyMuPDF

# Load configuration from file
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "default.yaml")
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

config = load_config()

# Get settings from config
QDRANT_URL = config['qdrant']['url']
QDRANT_COLLECTION = config['qdrant']['collection_name']

# Handle path differences between Docker container and local environment
# In Docker, the E:/AI Research is mapped to /app/data/pdfs
PDF_BASE_DIR = config['qdrant'].get('default_pdf_path', "E:/AI Research")
# If running in Docker, the path will be /app/data/pdfs
if os.path.exists("/app/data/pdfs"):
    print("Running in Docker environment, using /app/data/pdfs")
    PDF_BASE_DIR = "/app/data/pdfs"
else:
    print(f"Running in local environment, using {PDF_BASE_DIR}")

PROCESS_CATEGORIES = config['qdrant'].get('process_categories', [])
MAX_PAPERS_PER_CATEGORY = config['qdrant'].get('papers_per_category', 0)  # 0 means unlimited

# MongoDB tracking settings
MONGO_URI = config['mongo']['connection_string']
# Adjust MongoDB URI for local execution if needed
if MONGO_URI == "mongodb://mongodb:27017/" and not os.path.exists("/app"):
    # If running locally (not in Docker), use localhost instead of service name
    MONGO_URI = "mongodb://localhost:27017/"
    print(f"Adjusted MongoDB connection for local execution: {MONGO_URI}")

MONGO_DB = config['mongo']['db_name']
TRACKING_ENABLED = config['qdrant'].get('tracking', {}).get('enabled', False)
TRACKING_COLLECTION = config['qdrant'].get('tracking', {}).get('collection_name', 'processed_pdfs')
SYNC_WITH_QDRANT = config['qdrant'].get('tracking', {}).get('sync_with_qdrant', False)

# Initialize MongoDB client for tracking
mongo_client = None
tracking_collection = None

if TRACKING_ENABLED:
    try:
        mongo_client = MongoClient(MONGO_URI)
        tracking_collection = mongo_client[MONGO_DB][TRACKING_COLLECTION]
        print(f"MongoDB tracking enabled using collection: {TRACKING_COLLECTION}")
        
        # Create indexes if they don't exist
        tracking_collection.create_index("file_path", unique=True)
        tracking_collection.create_index("category")
        tracking_collection.create_index("processed_date")
    except Exception as e:
        print(f"Warning: Failed to initialize MongoDB tracking: {str(e)}")
        TRACKING_ENABLED = False

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file for unique identification."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()

def is_pdf_processed(file_path, category):
    """Check if a PDF has already been processed and stored in Qdrant."""
    if not TRACKING_ENABLED or tracking_collection is None:
        return False  # If tracking disabled, process all files
        
    # Generate a consistent file_id from the absolute path
    file_id = os.path.basename(file_path)
    
    # Check if file exists in tracking collection
    result = tracking_collection.find_one({"file_id": file_id, "category": category})
    return result is not None

def mark_pdf_as_processed(file_path, category, chunk_count):
    """Mark a PDF as processed in the tracking database."""
    if not TRACKING_ENABLED or tracking_collection is None:
        return
        
    # Generate metadata for tracking
    file_id = os.path.basename(file_path)
    file_hash = calculate_file_hash(file_path)
    
    # Store processing information
    tracking_info = {
        "file_id": file_id,
        "file_path": file_path,
        "category": category,
        "file_hash": file_hash,
        "chunk_count": chunk_count,
        "processed_date": datetime.datetime.now(),
    }
    
    # Insert or update the tracking record
    tracking_collection.update_one(
        {"file_id": file_id, "category": category},
        {"$set": tracking_info},
        upsert=True
    )
    
def sync_qdrant_with_tracking():
    """Synchronize MongoDB tracking with actual Qdrant contents."""
    if not TRACKING_ENABLED or not SYNC_WITH_QDRANT:
        return
    
    try:
        print("Syncing MongoDB tracking with Qdrant contents...")
        
        # Connect to Qdrant directly using the client to get metadata
        qdrant_client = QdrantClient(url=QDRANT_URL)
        
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if QDRANT_COLLECTION not in collection_names:
            print(f"Qdrant collection '{QDRANT_COLLECTION}' does not exist yet. No sync needed.")
            return
            
        # Get collection info to check if empty
        collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
        if collection_info.points_count == 0:
            print("Qdrant collection is empty. No sync needed.")
            return
        
        # Build a list of file_ids in MongoDB tracking
        tracked_files = set()
        for doc in tracking_collection.find({}, {"file_id": 1}):
            tracked_files.add(doc["file_id"])
            
        print(f"Currently tracking {len(tracked_files)} processed PDFs in MongoDB")
        print(f"Qdrant contains {collection_info.points_count} vector points")
        
        # If we have detailed information we could sync more precisely
        # For now, this is primarily setting up the structure for future enhancement
        
    except Exception as e:
        print(f"Error during Qdrant-MongoDB sync: {str(e)}")

def extract_images_from_pdf(pdf_path, output_dir):
    """Extract images from PDF and save to output_dir. Returns list of image file paths."""
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        for img_index, img in enumerate(doc.get_page_images(page_num)):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:  # this is GRAY or RGB
                img_path = os.path.join(output_dir, f"page{page_num+1}_img{img_index+1}.png")
                pix.save(img_path)
                image_paths.append(img_path)
            pix = None
    return image_paths

def process_pdf(pdf_path, qdrant_url=QDRANT_URL, qdrant_collection=QDRANT_COLLECTION):
    # 1. Load PDF and split text
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(pages)

    # 2. Embed and store text chunks in Qdrant using HuggingFace local embeddings with GPU if available
    # Get GPU settings from config
    gpu_enabled = config['qdrant'].get('gpu_enabled', False)
    gpu_device = config['qdrant'].get('gpu_device', 0)
    
    # Check if CUDA is actually available before attempting to use it
    import torch
    cuda_available = torch.cuda.is_available()
    
    # Determine device to use
    if gpu_enabled and cuda_available:
        try:
            # Validate that the requested GPU exists
            device = f"cuda:{gpu_device}" if gpu_device < torch.cuda.device_count() else "cuda:1"
            print(f"Using GPU for embeddings: {device}")
        except:
            device = "cpu"
            print("Error accessing GPU, falling back to CPU")
    else:
        device = "cpu"
        print("CUDA not available or not enabled, using CPU for embeddings")
    
    # Initialize embeddings with device
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": device}
    )
    
    # Create Qdrant collection
    vectorstore = Qdrant.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=qdrant_url,
        collection_name=qdrant_collection
    )

    # 3. Extract images from PDF
    image_dir = os.path.splitext(pdf_path)[0] + "_images"
    os.makedirs(image_dir, exist_ok=True)
    image_paths = extract_images_from_pdf(pdf_path, image_dir)

    # 4. Analyze images with local Ollama LLM (text-only, not vision) if available
    image_descriptions = []
    try:
        # Try to use Ollama for image analysis
        llm = Ollama(model="llama3")
        image_analysis_prompt = PromptTemplate(
            template="Describe this technical diagram in detail, including any labeled components: {image_path}",
            input_variables=["image_path"]
        )
        image_chain = LLMChain(llm=llm, prompt=image_analysis_prompt)
        
        for img_path in image_paths:
            try:
                # NOTE: Ollama llama3 is text-only; you can only pass the image path or a description, not the image itself.
                description = image_chain.run(image_path=img_path)
                image_descriptions.append({"file": img_path, "description": description})
            except Exception as e:
                print(f"Error analyzing image {img_path}: {str(e)}")
                # Add basic info without analysis
                image_descriptions.append({"file": img_path, "description": "[Analysis not available]"})  
    except Exception as e:
        print(f"Ollama image analysis not available: {str(e)}")
        print("Continuing without image analysis...")
        # Just add the image paths without analysis
        for img_path in image_paths:
            image_descriptions.append({"file": img_path, "description": "[Image analysis skipped - Ollama not available]"})

    return {
        "chunks": chunks,
        "images": image_descriptions,
    }

def process_all_categories():
    """Process PDFs from all specified categories in the config."""
    results = {}
    total_files_processed = 0
    
    # Sync MongoDB tracking with Qdrant if enabled
    if TRACKING_ENABLED and SYNC_WITH_QDRANT:
        sync_qdrant_with_tracking()
    
    print(f"Processing PDFs from categories: {PROCESS_CATEGORIES}")
    
    for category in PROCESS_CATEGORIES:
        category_dir = os.path.join(PDF_BASE_DIR, category)
        if not os.path.exists(category_dir):
            print(f"Category directory not found: {category_dir}")
            continue
            
        print(f"Processing category: {category}")
        pdf_files = [f for f in os.listdir(category_dir) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {category_dir}")
            continue
            
        print(f"Found {len(pdf_files)} PDF files in {category}")
        category_results = []
        
        # Filter out already processed PDFs if tracking is enabled
        if TRACKING_ENABLED:
            unprocessed_files = []
            processed_count = 0
            
            for pdf_file in pdf_files:
                pdf_path = os.path.join(category_dir, pdf_file)
                if is_pdf_processed(pdf_path, category):
                    processed_count += 1
                else:
                    unprocessed_files.append(pdf_file)
                    
            if processed_count > 0:
                print(f"Skipping {processed_count} already processed PDFs")
                
            pdf_files = unprocessed_files
            
            if not pdf_files:
                print(f"All PDFs in {category} have already been processed")
                continue
                
            print(f"Found {len(pdf_files)} unprocessed PDF files in {category}")
        
        # Apply the papers_per_category limit if set
        if MAX_PAPERS_PER_CATEGORY > 0 and len(pdf_files) > MAX_PAPERS_PER_CATEGORY:
            print(f"Limiting to {MAX_PAPERS_PER_CATEGORY} papers as per configuration")
            pdf_files = pdf_files[:MAX_PAPERS_PER_CATEGORY]
            
        for pdf_file in pdf_files:
            pdf_path = os.path.join(category_dir, pdf_file)
            try:
                print(f"Processing {pdf_file}...")
                result = process_pdf(pdf_path)
                
                # Record processing in MongoDB tracking
                if TRACKING_ENABLED:
                    mark_pdf_as_processed(pdf_path, category, len(result["chunks"]))
                
                category_results.append({
                    "file": pdf_file,
                    "chunks": len(result["chunks"]),
                    "images": len(result["images"])
                })
                total_files_processed += 1
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
        
        results[category] = category_results
    
    print(f"Total PDFs processed: {total_files_processed}")
    return results

if __name__ == "__main__":
    # Check if we have process_categories defined
    if PROCESS_CATEGORIES:
        # Process PDFs from all specified categories
        results = process_all_categories()
    else:
        # Fall back to processing a single PDF from the base directory
        test_pdf = os.path.join(PDF_BASE_DIR, next(os.walk(PDF_BASE_DIR))[2][0]) if os.path.exists(PDF_BASE_DIR) else None
        if test_pdf and test_pdf.endswith('.pdf'):
            print(f"Processing single PDF: {test_pdf}")
            result = process_pdf(test_pdf)
            print(f"Processed {len(result['chunks'])} chunks and {len(result['images'])} images")
        else:
            print(f"No PDF files found in {PDF_BASE_DIR}")
