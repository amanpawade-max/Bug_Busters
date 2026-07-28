import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.it_tools import reset_password, track_it_tickets, close_it_ticket
from tools.knowledge_tools import search_it_policy

load_dotenv()

IT_TOOLS = [reset_password, track_it_tickets, close_it_ticket, search_it_policy]

IT_SYSTEM_PROMPT = """You are the Enterprise IT Support Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. For policy FAQs ("What do I do if...", hardware rules, SLAs, software guidelines), call 'search_it_policy'.
2. ONLY call 'reset_password' if the user gives a direct command like "Reset my password".
3. When the user asks to TRACK, CHECK, VIEW, or MANAGE existing tickets (e.g., "track it ticket", "my tickets"), YOU MUST call 'track_it_tickets'. NEVER append form tokens for tracking!
4. To close or resolve an existing ticket, call 'close_it_ticket'.
5. When the user wants to REPORT A NEW ISSUE or RAISE A TICKET, do NOT call any tools. Reply with brief helpful words and include the plain text string [RENDER_TICKET_FORM] at the very end of your message.
CRITICAL: '[RENDER_TICKET_FORM]' is a PLAIN TEXT string. It is NOT a function or tool call! Do NOT attempt to invoke a tool named render_ticket_form.
6. You are operating in IT-only mode.
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