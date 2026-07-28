import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.finance_tools import get_reimbursement_status, track_expense_claims
from tools.knowledge_tools import search_finance_policy

load_dotenv()

# Notice: submit_expense_claim is EXCLUDED to prevent 400 parameter hallucination errors!
FINANCE_TOOLS = [get_reimbursement_status, track_expense_claims, search_finance_policy]

FINANCE_SYSTEM_PROMPT = """You are the Enterprise Finance Support Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. For questions about reimbursement batch dates, corporate card rules, receipt limits ($25 USD threshold), per diem rates, or rejected expense fixes, ALWAYS call 'search_finance_policy'. When the tool returns rules, YOU MUST summarize them conversationally!
2. To check payment status or reimbursement batch updates, call 'get_reimbursement_status'.
3. To view or track submitted expense reports, call 'track_expense_claims'.
4. If the user says they want to submit an expense, claim reimbursement, or report a business cost, DO NOT attempt to call an action tool. Instead, respond politely explaining what details are needed and append the exact token [RENDER_EXPENSE_FORM] at the very end of your message.
5. You are operating in Finance-only mode. If asked about HR leave or IT hardware tickets, politely explain that you can only assist with finance and expense reimbursement matters.
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