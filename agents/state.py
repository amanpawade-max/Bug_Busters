from typing import Annotated, TypedDict, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    The shared state dictionary passed between the Supervisor and Domain Agents.
    """
    # The running conversation transcript (automatically appends new messages)
    messages: Annotated[list, add_messages]
    
    # The active logged-in employee ID (defaults to EMP101)
    employee_id: str
    
    # Tracks which domain specialist last responded (HR, IT, FINANCE, TRAVEL, KNOWLEDGE)
    sender: Optional[str]
    
    # Used by the Supervisor Router to decide which node runs next
    next_step: Optional[str]