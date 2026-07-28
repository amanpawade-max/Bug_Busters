import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.it_tools import reset_password, track_it_tickets, close_it_ticket
from tools.knowledge_tools import search_it_policy

load_dotenv()

# Notice: raise_it_ticket is EXCLUDED here so Llama-8B cannot hallucinate or fail on it!
IT_TOOLS = [reset_password, track_it_tickets, close_it_ticket, search_it_policy]

IT_SYSTEM_PROMPT = """You are the Enterprise IT Support Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. For questions asking "What do I do if...", "How do I...", "Can I...", or questions about MFA devices, lost phones, hardware rules, SLAs, or software installation guidelines, ALWAYS call 'search_it_policy'. Do NOT call reset_password for FAQ questions!
2. ONLY call 'reset_password' if the user explicitly gives a direct command like "Reset my password right now" or "Send a password reset link".
3. To check ticket status or view active issues, call 'track_it_tickets'.
4. To close, cancel, or resolve an existing ticket (e.g., "close ticket INC-501"), call 'close_it_ticket'.
5. If the user reports a technical problem (WiFi down, mouse broken, need software) OR says "I want to raise a ticket", respond politely with brief troubleshooting advice and append the exact token [RENDER_TICKET_FORM] at the very end of your message.
6. You are operating in IT-only mode. If asked about HR leave or Finance expense claims, politely explain that you can only assist with IT matters.
"""

def get_it_agent_executor():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )
    llm_with_tools = llm.bind_tools(IT_TOOLS)
    tool_map = {t.name: t for t in IT_TOOLS}
    return llm_with_tools, tool_map