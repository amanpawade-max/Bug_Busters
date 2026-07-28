import os
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY"),
    model_kwargs={"response_format": {"type": "json_object"}}
)

SUPERVISOR_PROMPT = """You are the Supervisor Router for EnterpriseAssist AI.
Your job is to read the user's LATEST message and decide which specialist agent should act next.

Available Agents:
- HR: Leave requests, checking leave balance, applying for leave, employee profiles, holidays.
- IT: Password resets, raising support tickets, checking hardware/ticket status, software issues.
- FINANCE: Expense claims, reimbursement tracking, budget queries.
- TRAVEL: Business trip planning, travel budget estimates, booking requests.
- KNOWLEDGE: Searching company policies, remote work guidelines, security handbook.

Routing Rules (in priority order):
1. If the user asks about leave balance, remaining leaves, "how many leaves", "leaves left" → route to HR.
2. If the user wants to apply/submit/request/take leave → route to HR.
3. If the user mentions IT ticket, password reset, software install, hardware issue → route to IT.
4. If the user mentions expense, reimbursement, claim → route to FINANCE.
5. If the user mentions business travel, trip, flight booking → route to TRAVEL.
6. If the user asks about company policy, guidelines, rules → route to KNOWLEDGE.
7. If an agent has already answered the user's LATEST request with a complete response and no further tool execution is needed → output "FINISH".

IMPORTANT: Base your routing decision on the user's LATEST message only, not on old conversation history.
You MUST respond in valid JSON format with a single key "next_step". Example: {"next_step": "HR"}
"""

async def supervisor_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    # If the last message was from a domain agent and contains no tool calls, job is done
    if last_message and hasattr(last_message, "tool_calls") and not last_message.tool_calls and state.get("sender"):
        return {"next_step": "FINISH"}

    sys_msg = SystemMessage(content=SUPERVISOR_PROMPT)
    transcript = "\n".join([f"{m.type}: {m.content}" for m in messages[-4:]])
    user_msg = HumanMessage(content=f"Recent Conversation:\n{transcript}\n\nDecide next_step:")

    try:
        response = await llm.ainvoke([sys_msg, user_msg])
        raw_content = response.content.strip()
        
        # Clean up any markdown code blocks Llama-8b might add
        raw_content = re.sub(r"^```json\s*", "", raw_content)
        raw_content = re.sub(r"\s*```$", "", raw_content)
        
        decision = json.loads(raw_content)
        next_step = decision.get("next_step", "FINISH")
        
        if next_step not in ["HR", "IT", "FINANCE", "TRAVEL", "KNOWLEDGE", "FINISH"]:
            next_step = "FINISH"
    except Exception as e:
        print(f"⚠️ Supervisor Router Fallback triggered due to: {e}")
        next_step = "FINISH"

    return {"next_step": next_step}