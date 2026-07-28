import os
import glob
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# Configuration
KNOWLEDGE_BASE_DIR = "./knowledge_base"
CHROMA_PERSIST_DIR = "./chroma_db"
DOMAINS = ["hr", "it", "finance", "travel", "general"]

# Extremely fast ONNX embedding model (No PyTorch required!)
print("⏳ Loading FastEmbed model (BAAI/bge-small-en-v1.5)...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

def load_documents_for_domain(domain: str):
    domain_path = os.path.join(KNOWLEDGE_BASE_DIR, domain)
    if not os.path.exists(domain_path):
        os.makedirs(domain_path, exist_ok=True)
        print(f"⚠️ Created missing directory: {domain_path}. Drop files here!")
        return []

    docs = []
    # Load PDFs
    for pdf_path in glob.glob(os.path.join(domain_path, "**/*.pdf"), recursive=True):
        print(f"   📄 Loading PDF: {pdf_path}")
        loader = PyPDFLoader(pdf_path)
        docs.extend(loader.load())
        
    # Load TXT/Markdown
    for txt_path in glob.glob(os.path.join(domain_path, "**/*.txt"), recursive=True):
        print(f"   📄 Loading Text: {txt_path}")
        loader = TextLoader(txt_path, encoding="utf-8")
        docs.extend(loader.load())

    return docs

def ingest_all():
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=100,
        length_function=len
    )

    for domain in DOMAINS:
        print(f"\n--- Processing Domain: [{domain.upper()}] ---")
        raw_docs = load_documents_for_domain(domain)
        
        if not raw_docs:
            print(f"ℹ️ No documents found for {domain}, skipping...")
            continue

        chunked_docs = text_splitter.split_documents(raw_docs)
        print(f"🧩 Split into {len(chunked_docs)} chunks.")

        # Create/Update isolated collection in ChromaDB
        collection_name = f"{domain}_docs"
        vectorstore = Chroma.from_documents(
            documents=chunked_docs,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=CHROMA_PERSIST_DIR
        )
        print(f"✅ Saved to ChromaDB collection: '{collection_name}'")

if __name__ == "__main__":
    print("🚀 Starting Enterprise Knowledge Ingestion Pipeline...")
    ingest_all()
    print("\n🎉 Ingestion complete! All domain collections are ready for LangGraph agents.")