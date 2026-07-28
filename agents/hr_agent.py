import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.hr_tools import get_employee_profile, get_leave_balance, submit_leave_request, track_leave_requests
from tools.knowledge_tools import search_hr_policy

load_dotenv()

HR_TOOLS = [get_employee_profile, get_leave_balance, submit_leave_request, track_leave_requests, search_hr_policy]

HR_SYSTEM_PROMPT = """You are the Enterprise HR Specialist Assistant for Employee ID 'EMP101'.
YOUR RULES:
1. To check leave balances, call 'get_leave_balance'.
2. To check employee profile details, call 'get_employee_profile'.
3. When the user says "track", "my requests", "status", or "check my leave", YOU MUST call 'track_leave_requests'. Do NOT call search_hr_policy for tracking!
4. For questions about company rules, harassment, benefits, or HR guidelines, call 'search_hr_policy' directly.
5. When the user wants to APPLY for leave, do NOT call any tools. Reply politely and include the plain text string [RENDER_LEAVE_FORM] at the end of your message.
CRITICAL: '[RENDER_LEAVE_FORM]' is a PLAIN TEXT string. It is NOT a function or tool call!
6. You are operating in HR-only mode.
"""

def get_hr_agent_executor():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )
    llm_with_tools = llm.bind_tools(HR_TOOLS)
    tool_map = {t.name: t for t in HR_TOOLS}
    return llm_with_tools, tool_map