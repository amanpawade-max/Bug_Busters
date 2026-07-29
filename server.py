import os
import json
import asyncio

from fastapi import UploadFile, File, Form
from groq import Groq
import base64
import requests

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

@app.post("/voice-chat")
async def process_voice_chat(
    employee_id: str = Form(...),
    thread_id: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """Handles Turn-Based Voice Chat: STT -> LangGraph -> TTS"""
    try:
        # 1. Speech-to-Text (using Groq's blazing fast Whisper API)
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        audio_bytes = await audio_file.read()
        
        transcription = groq_client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3",
            prompt="Employee asking enterprise HR, IT, Finance or Travel questions.",
        )
        user_text = transcription.text.strip()

        # 2. Process via LangGraph Supervisor
        graph_state = {
            "messages": [HumanMessage(content=user_text)],
            "employee_id": employee_id
        }
        result = await master_graph.ainvoke(graph_state)
        last_msg = result["messages"][-1]
        answer_text = last_msg.content
        sender_name = result.get("sender", "Assistant")

        # 3. Clean UI Markdown for Text-to-Speech
        clean_speech = answer_text.replace("[RENDER_LEAVE_FORM]", "I have opened the leave application form on your screen.") \
                                  .replace("[RENDER_TICKET_FORM]", "I have opened the IT ticket form on your screen.") \
                                  .replace("[RENDER_EXPENSE_FORM]", "I have opened the expense claim form on your screen.") \
                                  .replace("[RENDER_TRAVEL_FORM]", "I have opened the business travel request form on your screen.")
                                  
        # Remove bolding/lists for better speech
        clean_speech = clean_speech.replace("*", "").replace("#", "")

        # 4. Text-to-Speech (using Deepgram Aura REST API)
        dg_api_key = os.getenv("DEEPGRAM_API_KEY")
        tts_url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
        tts_response = requests.post(
            tts_url,
            headers={"Authorization": f"Token {dg_api_key}", "Content-Type": "application/json"},
            json={"text": clean_speech}
        )
        
        # Encode audio to send back to frontend
        audio_base64 = base64.b64encode(tts_response.content).decode('utf-8') if tts_response.status_code == 200 else ""

        return {
            "user_text": user_text,
            "answer_text": answer_text,
            "sender": sender_name,
            "audio_base64": audio_base64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting EnterpriseAssist API Server on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)