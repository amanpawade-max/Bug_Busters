import os
import re
import asyncio
from dotenv import load_dotenv
import traceback

load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api
from agents.graph import get_compiled_graph
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Global graph reference initialized on startup
compiled_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compiled_graph
    compiled_graph = await get_compiled_graph()
    print("✅ LangGraph Multi-Agent Engine loaded and connected to SQLite.")
    yield
    print("🛑 Shutting down server...")

app = FastAPI(title="EnterpriseAssist AI Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenRequest(BaseModel):
    employee_id: str
    room_name: str

class ChatRequest(BaseModel):
    employee_id: str
    thread_id: str
    message: str


# ============================================================================
# INTENT DETECTION — Bypass LLM ambiguity for known simple queries
# ============================================================================
INTENT_PATTERNS = [
    (re.compile(
        r"how many (leave|leaves|day|days)|leave balance|leaves (left|remaining|do i have|left with)|"
        r"remaining (leave|leaves|days)|how much leave",
        re.IGNORECASE
    ), "[INTENT: CHECK_LEAVE_BALANCE]"),

    (re.compile(
        r"\b(apply|submit|request|take|book|want)\b.*(leave|vacation|off)",
        re.IGNORECASE
    ), "[INTENT: SUBMIT_LEAVE]"),

    (re.compile(
        r"\b(raise|create|log|open|submit)\b.*(ticket|issue|request)|it (ticket|support)",
        re.IGNORECASE
    ), "[INTENT: RAISE_IT_TICKET]"),

    (re.compile(
        r"(ticket|issue) (status|update)|check.*(ticket|issue)",
        re.IGNORECASE
    ), "[INTENT: CHECK_TICKET_STATUS]"),

    (re.compile(
        r"(reset|change|forgot|lost).*(password|pwd|pass)\b",
        re.IGNORECASE
    ), "[INTENT: RESET_PASSWORD]"),
]

def detect_and_tag_intent(message: str) -> str:
    """Prepend an [INTENT: ...] tag to the message if a known pattern matches."""
    for pattern, tag in INTENT_PATTERNS:
        if pattern.search(message):
            return f"{tag} {message}"
    return message


# ============================================================================
# RESPONSE EXTRACTION — Smart priority: Tool Results > AI Summaries
# ============================================================================
def extract_best_response(messages: list) -> str:
    """
    Priority order:
    1. Last ToolMessage with meaningful content (actual tool result)
    2. Last AIMessage without tool_calls (agent text summary)
    3. Any last non-empty string content
    """
    if not messages:
        return "I have processed your request."

    # First pass: prefer ToolMessage results
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.content and msg.content.strip():
            content = msg.content.strip()
            if "Action cancelled by user" not in content:
                return content

    # Second pass: last AIMessage without hallucinated follow-ups
    for msg in reversed(messages):
        if (isinstance(msg, AIMessage)
                and isinstance(msg.content, str)
                and msg.content.strip()
                and not getattr(msg, "tool_calls", None)):
            return msg.content.strip()

    # Fallback
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content.strip()

    return "I have processed your request."


async def _clear_hitl_state(config: dict, reason: str = "User cancelled request."):
    """
    Advances the graph past the sensitive_tools interrupt by injecting fake
    ToolMessages so state.next no longer points to sensitive_tools.
    """
    paused_state = await compiled_graph.aget_state(config)
    messages = paused_state.values.get("messages", [])
    last_msg = messages[-1] if messages else None

    tool_messages = []
    if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        for call in last_msg.tool_calls:
            tool_messages.append(
                ToolMessage(
                    content=f"Action cancelled by user: {reason}",
                    tool_call_id=call["id"],
                    name=call.get("name", "tool")
                )
            )
    
    if tool_messages:
        await compiled_graph.aupdate_state(
            config, {"messages": tool_messages}, as_node="sensitive_tools"
        )
    else:
        await compiled_graph.aupdate_state(
            config, {"messages": [AIMessage(content=reason)]}, as_node="sensitive_tools"
        )


@app.post("/get-token", status_code=status.HTTP_200_OK)
async def get_livekit_token(payload: TokenRequest):
    """Generates a secure LiveKit access token."""
    livekit_key = os.getenv("LIVEKIT_API_KEY")
    livekit_secret = os.getenv("LIVEKIT_API_SECRET")
    if not livekit_key or not livekit_secret:
        raise HTTPException(status_code=500, detail="LiveKit API Key or Secret missing.")
    try:
        grant = api.VideoGrants(
            room_join=True, room=payload.room_name,
            can_publish=True, can_subscribe=True, can_publish_data=True
        )
        token = (
            api.AccessToken(livekit_key, livekit_secret)
            .with_identity(payload.employee_id)
            .with_name(f"Employee {payload.employee_id}")
            .with_grants(grant)
        )
        return {"token": token.to_jwt(), "room": payload.room_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")


@app.post("/chat", status_code=status.HTTP_200_OK)
async def handle_text_chat(payload: ChatRequest):
    if not compiled_graph:
        raise HTTPException(status_code=503, detail="Graph engine not initialized.")

    config = {"configurable": {"thread_id": payload.thread_id}}
    
    try:
        current_state = await compiled_graph.aget_state(config)
        
        if current_state.next and "sensitive_tools" in current_state.next:
            user_msg = payload.message.strip().lower()
            approval_keywords = ["yes", "yep", "sure", "approve", "submit", "ok", "confirm", "go ahead", "do it"]
            decline_keywords = ["no", "cancel", "stop", "abort", "don't", "dont", "nope", "nah"]
            
            if any(k in user_msg for k in approval_keywords):
                # Resume the paused sensitive tool
                result = await compiled_graph.ainvoke(None, config=config)
                # Return tool result directly — skip the agent’s hallucinated follow-up
                post_messages = result.get("messages", [])
                response_text = extract_best_response(post_messages)
                return {
                    "response": f"✅ {response_text}",
                    "sender": result.get("sender", "Assistant"),
                    "thread_id": payload.thread_id,
                    "awaiting_approval": False
                }

            elif any(k in user_msg for k in decline_keywords):
                await _clear_hitl_state(config, reason="User declined this action.")
                return {
                    "response": "❌ Request cancelled. What else can I help you with?",
                    "sender": "System",
                    "thread_id": payload.thread_id,
                    "awaiting_approval": False
                }
            else:
                # Ambiguous — clear state and reprocess as fresh message
                await _clear_hitl_state(config, reason="Request cancelled — new message received.")
                tagged_message = detect_and_tag_intent(payload.message)
                input_message = HumanMessage(content=tagged_message)
                result = await compiled_graph.ainvoke(
                    {"messages": [input_message], "employee_id": payload.employee_id},
                    config=config
                )
        else:
            # Normal message — tag intent to help LLM agents
            tagged_message = detect_and_tag_intent(payload.message)
            input_message = HumanMessage(content=tagged_message)
            result = await compiled_graph.ainvoke(
                {"messages": [input_message], "employee_id": payload.employee_id},
                config=config
            )
        
        # Check if paused at HITL interrupt
        post_state = await compiled_graph.aget_state(config)
        if post_state.next and "sensitive_tools" in post_state.next:
            messages = post_state.values.get("messages", [])
            last_msg = messages[-1] if messages else None
            
            if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                call = last_msg.tool_calls[0]
                tool_name = call.get("name", "Action").replace("_", " ").title()
                args = call.get("args", {})
                details_str = "\n".join(
                    f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in args.items()
                )
                confirmation_text = (
                    f"HITL Confirmation Required\n\n"
                    f"Ready to submit **{tool_name}**:\n\n"
                    f"{details_str}\n\n"
                    f"Do you approve submitting this? (Reply Yes or No)"
                )
                return {
                    "response": confirmation_text,
                    "sender": post_state.values.get("sender", "Assistant"),
                    "thread_id": payload.thread_id,
                    "awaiting_approval": True
                }

        response_text = extract_best_response(result.get("messages", []))
        return {
            "response": response_text,
            "sender": result.get("sender", "Supervisor"),
            "thread_id": payload.thread_id,
            "awaiting_approval": False
        }
    except Exception as e:
        print("\n--- ERROR IN GRAPH EXECUTION ---")
        traceback.print_exc()
        print("------------------------------------\n")
        return {
            "response": f"I encountered an issue: {str(e)}. Please try rephrasing.",
            "sender": "System",
            "thread_id": payload.thread_id
        }


@app.delete("/clear-state/{thread_id}", status_code=status.HTTP_200_OK)
async def clear_thread_state(thread_id: str):
    """Debug endpoint to manually clear a stuck thread state."""
    if not compiled_graph:
        raise HTTPException(status_code=503, detail="Graph engine not initialized.")
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await compiled_graph.aget_state(config)
        if state.next and "sensitive_tools" in state.next:
            await _clear_hitl_state(config, reason="Manually cleared.")
            return {"status": "cleared", "thread_id": thread_id}
        return {"status": "no_pending_state", "thread_id": thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
