import os
import yaml
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
PDF_BASE_DIR = config['pdf_storage']['directory']
PROCESS_CATEGORIES = config['qdrant'].get('process_categories', [])

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

    # 2. Embed and store text chunks in Qdrant using HuggingFace local embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
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

    # 4. Analyze images with local Ollama LLM (text-only, not vision)
    llm = Ollama(model="llama3")
    image_analysis_prompt = PromptTemplate(
        template="Describe this technical diagram in detail, including any labeled components: {image_path}",
        input_variables=["image_path"]
    )
    image_chain = LLMChain(llm=llm, prompt=image_analysis_prompt)
    image_descriptions = []
    for img_path in image_paths:
        # NOTE: Ollama llama3 is text-only; you can only pass the image path or a description, not the image itself.
        description = image_chain.run(image_path=img_path)
        image_descriptions.append({"file": img_path, "description": description})

    return {
        "chunks": chunks,
        "images": image_descriptions,
    }

def process_all_categories():
    """Process PDFs from all specified categories in the config."""
    results = {}
    total_files_processed = 0
    
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
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(category_dir, pdf_file)
            try:
                print(f"Processing {pdf_file}...")
                result = process_pdf(pdf_path)
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
