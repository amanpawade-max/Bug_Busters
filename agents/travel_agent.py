import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.travel_tools import track_travel_requests
from tools.knowledge_tools import search_travel_policy

load_dotenv()

TRAVEL_TOOLS = [track_travel_requests, search_travel_policy]

TRAVEL_SYSTEM_PROMPT = """You are the Enterprise Travel Support Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. For flight booking rules, hotel rate limits, per-diem allowances, or travel partners, call 'search_travel_policy'.
2. To check status or view itineraries of existing travel requests, call 'track_travel_requests'.
3. When the user wants to PLAN A TRIP or REQUEST TRAVEL, do NOT call any tools. Reply politely and include the plain text string [RENDER_TRAVEL_FORM] at the end of your message.
CRITICAL: '[RENDER_TRAVEL_FORM]' is a PLAIN TEXT string. It is NOT a function or tool call!
4. You are operating in Travel-only mode.
"""

def get_travel_agent_executor():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )
    llm_with_tools = llm.bind_tools(TRAVEL_TOOLS)
    tool_map = {t.name: t for t in TRAVEL_TOOLS}
    return llm_with_tools, tool_map