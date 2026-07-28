import os
from langchain_core.tools import tool
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

CHROMA_PERSIST_DIR = "./chroma_db"
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

@tool
def search_hr_policy(query: str) -> str:
    """
    Searches EnterpriseCorp HR and General company policies (e.g., harassment, leave rules, benefits, guidelines).
    Takes a single search query string.
    """
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return "Error: Knowledge base database not found. Please run ingest.py first."

    try:
        hr_store = Chroma(collection_name="hr_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results = hr_store.similarity_search(query, k=2)
        
        gen_store = Chroma(collection_name="general_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results.extend(gen_store.similarity_search(query, k=1))

        if not results:
            return f"No specific HR or General policy found for: '{query}'."

        res_text = [f"### 📖 HR & Policy Guidelines Found:\n"]
        for idx, doc in enumerate(results, 1):
            clean_content = doc.page_content.replace("\n", " ").strip()
            res_text.append(f"* **Rule {idx}:** {clean_content}\n")
            
        res_text.append("\n[SYSTEM INSTRUCTION TO AI: You must read the rules above and answer the user's question conversationally in clear bullet points. Do NOT dump raw text or stay silent.]")
        return "\n".join(res_text)

    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"

@tool
def search_it_policy(query: str) -> str:
    """
    Searches EnterpriseCorp IT rules, hardware guidelines, software installation FAQs, and SLA policies.
    Takes a single search query string.
    """
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return "Error: Knowledge base database not found. Please run ingest.py first."

    try:
        it_store = Chroma(collection_name="it_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results = it_store.similarity_search(query, k=2)
        
        gen_store = Chroma(collection_name="general_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results.extend(gen_store.similarity_search(query, k=1))

        if not results:
            return f"No specific IT policy documentation found for: '{query}'."

        res_text = [f"### 🖥️ IT Policy Guidelines Found:\n"]
        for idx, doc in enumerate(results, 1):
            clean_content = doc.page_content.replace("\n", " ").strip()
            res_text.append(f"* **Guideline {idx}:** {clean_content}\n")
            
        res_text.append("\n[SYSTEM INSTRUCTION TO AI: You must read the guidelines above and answer the user's question conversationally in clear bullet points. Do NOT dump raw text or stay silent.]")
        return "\n".join(res_text)

    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"

@tool
def search_finance_policy(query: str) -> str:
    """
    Searches EnterpriseCorp Finance rules, corporate credit card guidelines, reimbursement timelines, per-diem allowances, and receipt thresholds.
    Takes a single search query string.
    """
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return "Error: Knowledge base database not found. Please run ingest.py first."

    try:
        fin_store = Chroma(collection_name="finance_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results = fin_store.similarity_search(query, k=2)
        
        gen_store = Chroma(collection_name="general_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results.extend(gen_store.similarity_search(query, k=1))

        if not results:
            return f"No specific Finance policy documentation found for: '{query}'."

        res_text = [f"### 💳 Finance Policy Guidelines Found:\n"]
        for idx, doc in enumerate(results, 1):
            clean_content = doc.page_content.replace("\n", " ").strip()
            res_text.append(f"* **Guideline {idx}:** {clean_content}\n")
            
        res_text.append("\n[SYSTEM INSTRUCTION TO AI: You must read the guidelines above and answer the user's question conversationally in clear bullet points. Do NOT dump raw text or stay silent.]")
        return "\n".join(res_text)

    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"

@tool
def search_travel_policy(query: str) -> str:
    """
    Searches EnterpriseCorp Travel rules, flight booking classes (Economy vs Business), hotel caps (Marriott/Hilton), per-diem daily allowances, and booking partners.
    Takes a single search query string.
    """
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return "Error: Knowledge base database not found. Please run ingest.py first."

    try:
        trv_store = Chroma(collection_name="travel_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results = trv_store.similarity_search(query, k=2)
        
        gen_store = Chroma(collection_name="general_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results.extend(gen_store.similarity_search(query, k=1))

        if not results:
            return f"No specific Travel policy documentation found for: '{query}'."

        res_text = [f"### ✈️ Travel Policy Guidelines Found:\n"]
        for idx, doc in enumerate(results, 1):
            clean_content = doc.page_content.replace("\n", " ").strip()
            res_text.append(f"* **Guideline {idx}:** {clean_content}\n")
            
        res_text.append("\n[SYSTEM INSTRUCTION TO AI: You must read the guidelines above and answer the user's question conversationally in clear bullet points. Do NOT dump raw text or stay silent.]")
        return "\n".join(res_text)

    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"