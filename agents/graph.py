import re
import json
import asyncio
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agents.state import AgentState
from agents.supervisor import route_user_request
from agents.hr_agent import get_hr_agent_executor, HR_SYSTEM_PROMPT
from agents.it_agent import get_it_agent_executor, IT_SYSTEM_PROMPT
from agents.finance_agent import get_finance_agent_executor, FINANCE_SYSTEM_PROMPT
from agents.travel_agent import get_travel_agent_executor, TRAVEL_SYSTEM_PROMPT
from agents.knowledge_agent import get_knowledge_agent_executor, KNOWLEDGE_SYSTEM_PROMPT

# Load all domain executors
hr_llm, hr_tools = get_hr_agent_executor()
it_llm, it_tools = get_it_agent_executor()
fin_llm, fin_tools = get_finance_agent_executor()
trv_llm, trv_tools = get_travel_agent_executor()
kno_llm, kno_tools = get_knowledge_agent_executor()

def extract_universal_tool_calls(text: str) -> list:
    """Catches broken <function=name>{"arg": "val"}</function> or raw name {"arg": "val"} leaks."""
    extracted = []
    # Try XML style
    xml_matches = re.findall(r"(?:<)?function=(\w+)>(.*?)(?:</function>|$)", text)
    for idx, (name, args_str) in enumerate(xml_matches):
        try:
            args = json.loads(args_str.strip())
            extracted.append({"name": name, "args": args, "id": f"call_xml_{idx}"})
        except Exception: pass
        
    if not extracted:
        # Try raw JSON style (e.g., search_travel_policy {"query": "..."})
        raw_matches = re.findall(r"(\w+)\s*(\{.*?\})", text)
        for idx, (name, args_str) in enumerate(raw_matches):
            try:
                args = json.loads(args_str.strip())
                extracted.append({"name": name, "args": args, "id": f"call_raw_{idx}"})
            except Exception: pass
            
    return extracted

# --- HELPER: Universal Node Executor ---
async def execute_domain_node(state: AgentState, llm_with_tools, tool_map, sys_prompt: str, sender_name: str):
    # CRITICAL BUG FIX: Dynamically inject the logged-in user's ID into the system prompt!
    active_emp_id = state.get("employee_id", "EMP101")
    dynamic_prompt = sys_prompt.replace("EMP101", active_emp_id)
    
    messages = [SystemMessage(content=dynamic_prompt)]
    
    for m in state["messages"][-8:]:
        if isinstance(m, HumanMessage):
            messages.append(m)
        elif isinstance(m, AIMessage):
            clean_c = m.content.replace("[RENDER_LEAVE_FORM]", "").replace("[RENDER_TICKET_FORM]", "").replace("[RENDER_EXPENSE_FORM]", "").replace("[RENDER_TRAVEL_FORM]", "").strip()
            if clean_c:
                messages.append(AIMessage(content=clean_c))
            
    response = await llm_with_tools.ainvoke(messages)
    tool_calls = response.tool_calls if hasattr(response, "tool_calls") and response.tool_calls else []
    
    # FALLBACK: Check if 8B model leaked the tool call into plain text!
    if not tool_calls and any(kw in response.content for kw in ["function=", "search_", "track_", "get_", "reset_", "close_"]):
        leaked_calls = extract_universal_tool_calls(response.content)
        if leaked_calls:
            tool_calls = leaked_calls
            response = AIMessage(content="", tool_calls=tool_calls)
    
    if tool_calls:
        messages.append(response)
        rendered_outputs = []
        for tc in tool_calls:
            t_name, t_args, t_id = tc["name"], tc["args"], tc.get("id", f"call_{tc['name']}")
            if t_name in tool_map:
                res_card = tool_map[t_name].invoke(t_args)
                rendered_outputs.append(res_card)
                messages.append(ToolMessage(content=res_card, tool_call_id=t_id))
            else:
                err = f"Error: Tool {t_name} not found."
                rendered_outputs.append(err)
                messages.append(ToolMessage(content=err, tool_call_id=t_id))
                
        final_res = await llm_with_tools.ainvoke(messages)
        final_text = final_res.content.strip()
        display = final_text if final_text and "function=" not in final_text and "{" not in final_text else "\n\n".join(rendered_outputs)
        return {"messages": [AIMessage(content=display)], "sender": sender_name}
    else:
        return {"messages": [response], "sender": sender_name}

        
# --- NODE DEFINITIONS ---
async def supervisor_node(state: AgentState):
    latest_user_msg = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            latest_user_msg = m.content
            break
            
    next_dest = await route_user_request(latest_user_msg)
    return {"next_step": next_dest, "sender": "SUPERVISOR"}

async def hr_node(state: AgentState): return await execute_domain_node(state, hr_llm, hr_tools, HR_SYSTEM_PROMPT, "HR Specialist")
async def it_node(state: AgentState): return await execute_domain_node(state, it_llm, it_tools, IT_SYSTEM_PROMPT, "IT Support")
async def fin_node(state: AgentState): return await execute_domain_node(state, fin_llm, fin_tools, FINANCE_SYSTEM_PROMPT, "Finance Assistant")
async def trv_node(state: AgentState): return await execute_domain_node(state, trv_llm, trv_tools, TRAVEL_SYSTEM_PROMPT, "Travel Desk")
async def kno_node(state: AgentState): return await execute_domain_node(state, kno_llm, kno_tools, KNOWLEDGE_SYSTEM_PROMPT, "Knowledge Assistant")

def route_next(state: AgentState):
    return state.get("next_step", "KNOWLEDGE")

def build_master_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("SUPERVISOR", supervisor_node)
    workflow.add_node("HR", hr_node)
    workflow.add_node("IT", it_node)
    workflow.add_node("FINANCE", fin_node)
    workflow.add_node("TRAVEL", trv_node)
    workflow.add_node("KNOWLEDGE", kno_node)
    
    workflow.add_edge(START, "SUPERVISOR")
    workflow.add_conditional_edges(
        "SUPERVISOR",
        route_next,
        {"HR": "HR", "IT": "IT", "FINANCE": "FINANCE", "TRAVEL": "TRAVEL", "KNOWLEDGE": "KNOWLEDGE"}
    )
    
    for node_name in ["HR", "IT", "FINANCE", "TRAVEL", "KNOWLEDGE"]:
        workflow.add_edge(node_name, END)
        
    return workflow.compile()