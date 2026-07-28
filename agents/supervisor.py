import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

SUPERVISOR_PROMPT = """You are the Enterprise Assist Master Supervisor Router.
Your ONLY job is to classify the user's request and output EXACTLY ONE word corresponding to the destination department.

DESTINATIONS:
- HR: Leave balances, casual/sick/annual leaves, applying for leave, leave tracking, employee profile details, anti-harassment, or HR FAQs.
- IT: WiFi, hardware/software, laptop issues, IT support tickets, password resets, MFA devices, or technical helpdesk.
- FINANCE: Expense reports, reimbursement claims, corporate credit cards, receipt rules, or payout batch dates.
- TRAVEL: Business trip planning, flight rules, hotel rate caps, per-diem allowances, or travel itineraries.
- KNOWLEDGE: General company policy, Code of Conduct, remote work rules, or general ethics.

CRITICAL RULES:
1. Output ONLY ONE WORD from this list: [HR, IT, FINANCE, TRAVEL, KNOWLEDGE].
2. If the user types a short conversational word like "cancel", "nevermind", "stop", "hello", or "help", DO NOT default to HR! Route them to KNOWLEDGE instead.
"""

def get_supervisor_router():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        api_key=os.getenv("GROQ_API_KEY")
    )

async def route_user_request(user_message: str) -> str:
    """Invokes supervisor model and returns a clean destination string."""
    llm = get_supervisor_router()
    prompt = [SystemMessage(content=SUPERVISOR_PROMPT), HumanMessage(content=user_message)]
    
    try:
        response = await llm.ainvoke(prompt)
        text = response.content.strip().upper()
        
        # Clean potential markdown formatting
        for dept in ["HR", "IT", "FINANCE", "TRAVEL", "KNOWLEDGE"]:
            if dept in text:
                return dept
        return "KNOWLEDGE"
    except Exception:
        return "KNOWLEDGE"