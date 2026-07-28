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
3. To track existing leave applications or check approval status, call 'track_leave_requests'.
4. For questions about company rules, harassment, benefits, or HR policies, call 'search_hr_policy'. When the tool returns policy rules, YOU MUST summarize those rules conversationally to answer the user's question!
5. When the user says they want to apply for leave, request time off, or take vacation, DO NOT call 'submit_leave_request'. Instead, respond politely and append the exact token [RENDER_LEAVE_FORM] at the very end of your message.
6. You are operating in HR-only mode. If asked about IT or Finance, explain that you can only assist with HR matters.
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