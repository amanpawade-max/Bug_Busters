import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.finance_tools import get_reimbursement_status, track_expense_claims
from tools.knowledge_tools import search_finance_policy

load_dotenv()

FINANCE_TOOLS = [get_reimbursement_status, track_expense_claims, search_finance_policy]

FINANCE_SYSTEM_PROMPT = """You are the Enterprise Finance Support Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. For questions about reimbursement rules, receipt limits ($25 USD threshold), per diems, or card rules, call 'search_finance_policy'.
2. To check payment status or reimbursement batch updates, call 'get_reimbursement_status'.
3. To view or track submitted expense reports, call 'track_expense_claims'.
4. When the user wants to SUBMIT AN EXPENSE or CLAIM REIMBURSEMENT, do NOT call any tools. Reply politely and include the plain text string [RENDER_EXPENSE_FORM] at the end of your message.
CRITICAL: '[RENDER_EXPENSE_FORM]' is a PLAIN TEXT string. It is NOT a function or tool call!
5. You are operating in Finance-only mode.
"""

def get_finance_agent_executor():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )
    llm_with_tools = llm.bind_tools(FINANCE_TOOLS)
    tool_map = {t.name: t for t in FINANCE_TOOLS}
    return llm_with_tools, tool_map