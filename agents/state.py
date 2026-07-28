from typing import Annotated, TypedDict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Shared state clipboard passed between the Supervisor, Domain Agents, and Tool Nodes.
    """
    # Automatically appends new messages to history instead of overwriting
    messages: Annotated[list[AnyMessage], add_messages]
    
    # Active employee context (e.g., "EMP101")
    employee_id: str
    
    # Routing tag set by Supervisor ('HR', 'IT', 'FINANCE', 'TRAVEL', 'KNOWLEDGE', or 'FINISH')
    next_step: str
    
    # Tracks which domain agent called a tool so the ToolNode can loop back to it
    sender: str
    
    # Placeholder for Phase 2 proactive background alerts
    proactive_event: Optional[dict[str, Any]]