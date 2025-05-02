import os
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

QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "arxiv_papers"

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

if __name__ == "__main__":
    # Set the path to your PDF file here
    pdf_path = "E:/AI Research/2504.09647v1.pdf"
    result = process_pdf(pdf_path)
    print(result)