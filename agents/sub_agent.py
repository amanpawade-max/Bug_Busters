import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from agents.state import AgentState

# Import safe read-only tools
from tools.hr_tools import get_employee_profile, get_leave_balance
from tools.it_tools import check_ticket_status, reset_password
from tools.finance_tools import get_reimbursement_status
from tools.knowledge_tools import search_company_policy

# Import sensitive write tools (HITL required)
from tools.hr_tools import submit_leave_request
from tools.it_tools import raise_it_ticket
from tools.finance_tools import submit_expense_claim
from tools.travel_tools import request_business_travel

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY")
)

# --- Define Tool Toolboxes ---
HR_TOOLS = [get_employee_profile, get_leave_balance, submit_leave_request, search_company_policy]
IT_TOOLS = [check_ticket_status, reset_password, raise_it_ticket, search_company_policy]
FINANCE_TOOLS = [get_reimbursement_status, submit_expense_claim, search_company_policy]
TRAVEL_TOOLS = [request_business_travel, search_company_policy]
KNOWLEDGE_TOOLS = [search_company_policy]

# ============================================================================
# STRICT UNIVERSAL SYSTEM RULES
# ============================================================================
STRICT_SYSTEM_RULES = """
### ABSOLUTE EXECUTION DIRECTIVES:
1. **DATE PARSING CONTEXT:** Current Year is 2026 (Today's Date: 2026-07-27). When users specify natural dates like "3rd August" or "3rd Aug to 6th Aug", convert them into YYYY-MM-DD format (e.g. '2026-08-03' to '2026-08-06'). Treat natural dates as valid dates!
2. **CURRENT INTENT ONLY:** Base your action on the user's CURRENT/LATEST message intent. Do NOT assume the user wants to continue or repeat an action from a previous turn just because those details exist in chat history.
3. **AUTOMATIC DURATION:** Do NOT argue with the user over day counts. The backend tool automatically computes duration from start_date and end_date.
4. **DIRECT TOOL INVOCATION:** Once you have gathered all required details, IMMEDIATELY call the appropriate backend tool.
5. **NO PSEUDO-CODE:** Never write raw code, function names, or tags like '<function=...>' in plain text.
6. **AFTER TOOL SUCCESS (CRITICAL):** When the conversation shows a ToolMessage with a successful result, output ONLY a brief 1-2 sentence confirmation of that result. Do NOT ask follow-up questions. Do NOT offer additional services. Do NOT suggest other actions. STOP.
7. **[INTENT] TAGS:** The user's message may be prefixed with an [INTENT: ...] tag (e.g. [INTENT: CHECK_LEAVE_BALANCE]). These tags take highest priority over any other reasoning. Always act on the intent tag first.
"""

def get_trimmed_messages(messages, max_turns=6):
    """Keep only the last N messages to prevent stale context from bleeding into new requests."""
    if len(messages) <= max_turns:
        return messages
    return messages[-max_turns:]


# ============================================================================
# 1. HR AGENT NODE
# ============================================================================
async def hr_agent_node(state: AgentState) -> dict:
    llm_with_tools = llm.bind_tools(HR_TOOLS)
    emp_id = state.get('employee_id', 'EMP101')
    
    # Fast-path: check latest user message for [INTENT: CHECK_LEAVE_BALANCE]
    messages_list = state.get("messages", [])
    latest_user_msg = ""
    for msg in reversed(messages_list):
        if hasattr(msg, 'type') and msg.type == 'human':
            latest_user_msg = msg.content.lower()
            break
    
    sys_prompt = SystemMessage(content=(
        f"You are the Enterprise HR Assistant for employee '{emp_id}'.\n"
        "Your available tools are: get_employee_profile, get_leave_balance, submit_leave_request, and search_company_policy.\n\n"
        "## CRITICAL DECISION RULES (follow in order):\n\n"
        "### RULE 1 — INTENT TAG (HIGHEST PRIORITY):\n"
        "If the user's message starts with [INTENT: CHECK_LEAVE_BALANCE] → you MUST call get_leave_balance IMMEDIATELY. "
        "Do NOT call any other tool. Do NOT ask any questions.\n\n"
        "### RULE 2 — BALANCE CHECK KEYWORDS:\n"
        "If the user's latest message contains ANY of: 'how many leaves', 'leave balance', 'leaves left', "
        "'remaining leaves', 'leaves do i have', 'leaves left with', 'how much leave' → "
        "call get_leave_balance IMMEDIATELY. NEVER call submit_leave_request.\n\n"
        "### RULE 3 — VIEW PROFILE:\n"
        "If user asks about their profile, role, or department → call get_employee_profile.\n\n"
        "### RULE 4 — SUBMIT LEAVE (ONLY when user explicitly requests in CURRENT message):\n"
        "ONLY call submit_leave_request when [INTENT: SUBMIT_LEAVE] is present OR the CURRENT message "
        "explicitly contains 'apply for leave', 'submit leave', 'request leave', 'take leave', 'want leave', 'book leave'.\n"
        f"Required args: emp_id='{emp_id}', leave_type (casual/sick/annual), start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), reason.\n"
        "Ask for ONE missing piece at a time. Convert 'Aug 3' to '2026-08-03'.\n\n"
        "### RULE 5 — POLICY:\n"
        "If user asks about policies → call search_company_policy.\n\n"
        f"{STRICT_SYSTEM_RULES}"
    ))
    
    messages = [sys_prompt] + get_trimmed_messages(state["messages"])
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        print(f"Warning HR Agent: {e}. Falling back.")
        response = await llm.ainvoke(messages)
    return {"messages": [response], "sender": "HR"}



# ============================================================================
# 2. IT AGENT NODE
# ============================================================================
async def it_agent_node(state: AgentState) -> dict:
    llm_with_tools = llm.bind_tools(IT_TOOLS)
    emp_id = state.get('employee_id', 'EMP101')
    
    sys_prompt = SystemMessage(content=(
        f"You are the Enterprise IT Support Assistant for employee '{emp_id}'.\n"
        "Your available tools are: check_ticket_status, reset_password, raise_it_ticket, and search_company_policy.\n\n"
        "## CRITICAL RULES:\n\n"
        "### RULE 1 — INTENT TAG (HIGHEST PRIORITY):\n"
        "If message has [INTENT: RAISE_IT_TICKET] → collect category and description, then call raise_it_ticket.\n"
        "If message has [INTENT: CHECK_TICKET_STATUS] → call check_ticket_status.\n"
        "If message has [INTENT: RESET_PASSWORD] → call reset_password.\n\n"
        "### RULE 2 — RAISE IT TICKET:\n"
        f"Required args: emp_id='{emp_id}', category (Software/Hardware/Network/Access/Permissions/General), issue_description, priority (LOW/MEDIUM/HIGH/URGENT, default MEDIUM).\n"
        "If category or description is missing, ask for them clearly with the category options listed.\n"
        "Once details are provided, call raise_it_ticket immediately.\n\n"
        "### RULE 3 — AFTER TOOL SUCCESS:\n"
        "When a raise_it_ticket or reset_password tool has returned a SUCCESS result, output ONLY a "
        "1-sentence confirmation like 'Your IT ticket has been raised successfully.' "
        "Do NOT ask follow-up questions. Do NOT offer password resets or other services unprompted.\n\n"
        f"{STRICT_SYSTEM_RULES}"
    ))
    
    messages = [sys_prompt] + get_trimmed_messages(state["messages"])
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        print(f"Warning IT Agent: {e}. Falling back.")
        response = await llm.ainvoke(messages)
    return {"messages": [response], "sender": "IT"}


# ============================================================================
# 3. FINANCE AGENT NODE
# ============================================================================
async def finance_agent_node(state: AgentState) -> dict:
    llm_with_tools = llm.bind_tools(FINANCE_TOOLS)
    emp_id = state.get('employee_id', 'EMP101')
    
    sys_prompt = SystemMessage(content=(
        f"You are the Enterprise Finance Assistant for employee '{emp_id}'.\n"
        "Your available tools are: get_reimbursement_status, submit_expense_claim, and search_company_policy.\n\n"
        "RULES FOR EXPENSE CLAIMS (submit_expense_claim):\n"
        "- Required arguments: emp_id, category, amount (float), description.\n"
        "- Read all previous turns to extract amount and description. If missing, ask for details.\n"
        "- Once details are available, invoke submit_expense_claim natively with emp_id='{emp_id}'.\n\n"
        f"{STRICT_SYSTEM_RULES}"
    ))
    
    messages = [sys_prompt] + get_trimmed_messages(state["messages"])
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        print(f"⚠️ Finance Agent Tool Call Error: {e}. Falling back to standard generation.")
        response = await llm.ainvoke(messages)
    return {"messages": [response], "sender": "FINANCE"}


# ============================================================================
# 4. TRAVEL AGENT NODE
# ============================================================================
async def travel_agent_node(state: AgentState) -> dict:
    llm_with_tools = llm.bind_tools(TRAVEL_TOOLS)
    emp_id = state.get('employee_id', 'EMP101')
    
    sys_prompt = SystemMessage(content=(
        f"You are the Enterprise Travel Assistant for employee '{emp_id}'.\n"
        "Your available tools are: request_business_travel and search_company_policy.\n\n"
        "RULES FOR TRAVEL REQUESTS (request_business_travel):\n"
        "- Required arguments: emp_id, destination, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), estimated_budget (float).\n"
        "- Read all previous turns to extract destination, dates (YYYY-MM-DD using year 2026), and budget.\n"
        "- Once details are available, invoke request_business_travel natively with emp_id='{emp_id}'.\n\n"
        f"{STRICT_SYSTEM_RULES}"
    ))
    
    messages = [sys_prompt] + get_trimmed_messages(state["messages"])
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        print(f"⚠️ Travel Agent Tool Call Error: {e}. Falling back to standard generation.")
        response = await llm.ainvoke(messages)
    return {"messages": [response], "sender": "TRAVEL"}


# ============================================================================
# 5. KNOWLEDGE BASE AGENT NODE
# ============================================================================
async def knowledge_agent_node(state: AgentState) -> dict:
    llm_with_tools = llm.bind_tools(KNOWLEDGE_TOOLS)
    
    sys_prompt = SystemMessage(content=(
        "You are the Enterprise Knowledge & Policy Assistant.\n"
        "Your available tool is: search_company_policy.\n"
        "Use search_company_policy to search company guidelines and policies.\n\n"
        f"{STRICT_SYSTEM_RULES}"
    ))
    
    messages = [sys_prompt] + get_trimmed_messages(state["messages"])
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        print(f"⚠️ Knowledge Agent Tool Call Error: {e}. Falling back to standard generation.")
        response = await llm.ainvoke(messages)
    return {"messages": [response], "sender": "KNOWLEDGE"}