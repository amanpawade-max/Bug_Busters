import os
import aiosqlite
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agents.state import AgentState
from agents.supervisor import supervisor_node
from agents.sub_agent import (
    hr_agent_node, it_agent_node, finance_agent_node, 
    travel_agent_node, knowledge_agent_node
)

# Import tools for categorization
from tools.hr_tools import get_employee_profile, submit_leave_request, get_leave_balance
from tools.it_tools import check_ticket_status, reset_password, raise_it_ticket
from tools.finance_tools import get_reimbursement_status, submit_expense_claim
from tools.travel_tools import request_business_travel
from tools.knowledge_tools import search_company_policy


SAFE_TOOLS = [
    get_employee_profile, 
    get_leave_balance, 
    check_ticket_status, 
    reset_password, 
    get_reimbursement_status, 
    search_company_policy
]

SENSITIVE_TOOLS = [
    submit_leave_request, raise_it_ticket, submit_expense_claim, request_business_travel
]

safe_tools_node = ToolNode(SAFE_TOOLS)
sensitive_tools_node = ToolNode(SENSITIVE_TOOLS)

# 2. Build the Workflow StateGraph
builder = StateGraph(AgentState)

# Add all nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("HR", hr_agent_node)
builder.add_node("IT", it_agent_node)
builder.add_node("FINANCE", finance_agent_node)
builder.add_node("TRAVEL", travel_agent_node)
builder.add_node("KNOWLEDGE", knowledge_agent_node)
builder.add_node("safe_tools", safe_tools_node)
builder.add_node("sensitive_tools", sensitive_tools_node)

# 3. Define Edge Routing Functions
def route_from_supervisor(state: AgentState) -> str:
    return state.get("next_step", "FINISH")

def route_from_agent(state: AgentState) -> str:
    """Inspects agent output: routes to safe tools, sensitive tools, or back to supervisor."""
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    
    if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        sensitive_names = [t.name for t in SENSITIVE_TOOLS]
        safe_names = [t.name for t in SAFE_TOOLS]
        for call in last_msg.tool_calls:
            if call["name"] in sensitive_names:
                return "sensitive_tools"
            elif call["name"] in safe_names:
                return "safe_tools"
    return "supervisor"

def route_from_tool(state: AgentState) -> str:
    """Returns execution flow back to the domain worker that called the tool."""
    return state.get("sender", "supervisor")

# 4. Wire the Graph Edges
builder.add_edge(START, "supervisor")

# Supervisor routes to domains or END
builder.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "HR": "HR",
        "IT": "IT",
        "FINANCE": "FINANCE",
        "TRAVEL": "TRAVEL",
        "KNOWLEDGE": "KNOWLEDGE",
        "FINISH": END
    }
)

# Domain agents route to tools or back to supervisor
for domain in ["HR", "IT", "FINANCE", "TRAVEL", "KNOWLEDGE"]:
    builder.add_conditional_edges(
        domain,
        route_from_agent,
        {"safe_tools": "safe_tools", "sensitive_tools": "sensitive_tools", "supervisor": "supervisor"}
    )

# Tool nodes loop back to the originating sender agent
builder.add_conditional_edges("safe_tools", route_from_tool, {d: d for d in ["HR", "IT", "FINANCE", "TRAVEL", "KNOWLEDGE"]})
builder.add_conditional_edges("sensitive_tools", route_from_tool, {d: d for d in ["HR", "IT", "FINANCE", "TRAVEL", "KNOWLEDGE"]})

DB_PATH = "data/checkpoints.sqlite"
os.makedirs("data", exist_ok=True)

async def get_compiled_graph():
    """Returns the compiled asynchronous workflow graph with persistent memory."""
    # Create a direct asynchronous SQLite connection
    conn = await aiosqlite.connect(DB_PATH)
    
    # Initialize the saver directly with the connection object
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()  # Safely ensures checkpoint tables exist in SQLite
    
    # Compile with HITL execution freeze
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["sensitive_tools"]
    )
    return graph