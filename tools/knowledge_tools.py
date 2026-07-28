import os
from langchain_core.tools import tool
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

CHROMA_PERSIST_DIR = "./chroma_db"
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

@tool
def search_company_policy(query: str, domain: str = "general") -> str:
    """
    Searches EnterpriseCorp company policies and documentation.
    Allowed domain values: 'hr', 'it', 'finance', 'travel', 'general'.
    """
    collection_name = f"{domain.lower()}_docs"
    
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return "Knowledge base index not found. Please run ingest.py first."

    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        results = vectorstore.similarity_search(query, k=3)
        if not results:
            return f"No specific policy documentation found in {domain} for query: '{query}'."

        res_text = [f"Found {len(results)} relevant policy excerpt(s) in [{domain.upper()}]:"]
        for idx, doc in enumerate(results, 1):
            res_text.append(f"\n--- Excerpt {idx} ---\n{doc.page_content}")
        return "\n".join(res_text)

    except Exception as e:
        return f"Error querying vector store for domain {domain}: {str(e)}"