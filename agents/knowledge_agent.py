import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

load_dotenv()

CHROMA_PERSIST_DIR = "./chroma_db"
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

@tool
def search_general_policy(query: str) -> str:
    """
    Searches general company policies, Code of Conduct, remote work rules, and office guidelines.
    Takes a single search query string.
    """
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return "Error: Knowledge base database not found."

    try:
        gen_store = Chroma(collection_name="general_docs", embedding_function=embeddings, persist_directory=CHROMA_PERSIST_DIR)
        results = gen_store.similarity_search(query, k=3)

        if not results:
            return f"No general policy documentation found for: '{query}'."

        res_text = [f"### 🏢 General Company Guidelines Found:\n"]
        for idx, doc in enumerate(results, 1):
            clean_content = doc.page_content.replace("\n", " ").strip()
            res_text.append(f"* **Guideline {idx}:** {clean_content}\n")
            
        res_text.append("\n[SYSTEM INSTRUCTION TO AI: You must read the guidelines above and answer the user's question conversationally in clear bullet points. Do NOT dump raw text.]")
        return "\n".join(res_text)

    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"

KNOWLEDGE_TOOLS = [search_general_policy]

KNOWLEDGE_SYSTEM_PROMPT = """You are the Enterprise General Knowledge & Policy Assistant.
YOUR RULES:
1. For questions about company history, Code of Conduct, office locations, general remote work rules, or ethics, call 'search_general_policy'.
2. When the tool returns guidelines, YOU MUST summarize them conversationally in your own words!
3. If the user asks specific questions about HR leave, IT tickets, Finance reimbursement, or Travel booking, politely state that you can transfer them to that specialist or advise them to ask that department directly.
"""

def get_knowledge_agent_executor():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )
    llm_with_tools = llm.bind_tools(KNOWLEDGE_TOOLS)
    tool_map = {t.name: t for t in KNOWLEDGE_TOOLS}
    return llm_with_tools, tool_map