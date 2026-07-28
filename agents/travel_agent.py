import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.travel_tools import track_travel_requests
from tools.knowledge_tools import search_travel_policy

load_dotenv()

# Notice: submit_travel_request is EXCLUDED to prevent parameter hallucination!
TRAVEL_TOOLS = [track_travel_requests, search_travel_policy]

TRAVEL_SYSTEM_PROMPT = """You are the Enterprise Travel Support Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. For questions about flight booking rules (Economy under 6 hours, Business over 6 hours), hotel rate limits (NYC vs Mumbai caps), per-diem allowances, or travel partners, ALWAYS call 'search_travel_policy'. When the tool returns rules, YOU MUST summarize them conversationally!
2. To check the status or view itineraries of existing travel requests, call 'track_travel_requests'.
3. If the user says they want to plan a trip, book travel, request a business trip, or generate a travel plan, DO NOT attempt to call an action tool. Instead, respond politely explaining what details are needed and append the exact token [RENDER_TRAVEL_FORM] at the very end of your message.
4. You are operating in Travel-only mode. If asked about HR leave, IT hardware, or Finance expense claims, politely explain that you can only assist with travel planning and trip policies.
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