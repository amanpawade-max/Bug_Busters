import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from livekit.api import AccessToken, VideoGrants
from langchain_core.messages import HumanMessage, AIMessage
from agents.graph import build_master_graph

load_dotenv()

app = FastAPI(title="EnterpriseAssist API Server", version="2.0")

# Allow Streamlit frontend to access endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LangGraph Engine once
master_graph = build_master_graph()

class TokenRequest(BaseModel):
    employee_id: str
    room_name: str

class ChatRequest(BaseModel):
    employee_id: str
    thread_id: str
    message: str

@app.get("/")
def health_check():
    return {"status": "ONLINE", "service": "EnterpriseAssist Uplink"}

@app.post("/get-token")
def get_livekit_token(req: TokenRequest):
    """Generates a secure LiveKit JWT Access Token for WebRTC voice communication."""
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=500, detail="LiveKit API keys not configured in .env")

    try:
        # Create token valid for 15 minutes (900 seconds)
        token = AccessToken(api_key, api_secret)
        token.with_identity(req.employee_id)
        token.with_name(f"Employee {req.employee_id}")
        
        # Grant room join and audio publish/subscribe permissions
        grants = VideoGrants(
            room_join=True,
            room=req.room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )
        token.with_grants(grants)
        
        jwt_token = token.to_jwt()
        return {"token": jwt_token, "room_name": req.room_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")

@app.post("/chat")
async def process_chat(req: ChatRequest):
    """Processes text queries or proactive alerts via the LangGraph 5-Agent Supervisor."""
    try:
        graph_state = {
            "messages": [HumanMessage(content=req.message)],
            "employee_id": req.employee_id
        }
        result = await master_graph.ainvoke(graph_state)
        last_msg = result["messages"][-1]
        return {"response": last_msg.content, "sender": result.get("sender", "Assistant")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting EnterpriseAssist API Server on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)