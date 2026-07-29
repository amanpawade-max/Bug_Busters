import os
import json
import asyncio
import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, silero, groq
from langchain_core.messages import HumanMessage
from agents.graph import build_master_graph

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EnterpriseVoiceWorker")

master_graph = build_master_graph()

# ============================================================
# Helper: Sync Voice Transcripts to sessions.json (For UI Chat Box)
# ============================================================
def log_to_sessions_json(emp_id: str, role: str, text: str):
    """Writes voice turns to sessions.json so they appear in the Streamlit text chat UI!"""
    try:
        if not os.path.exists("sessions.json"):
            return
        with open("sessions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if emp_id not in data:
            return
            
        # Write to the employee's active/latest thread
        threads = list(data[emp_id].keys())
        if not threads:
            return
        active_thread = threads[0]
        
        data[emp_id][active_thread].append({
            "role": role,
            "content": text,
            "sender": "Aiden (Voice)" if role == "assistant" else f"Employee {emp_id} (Voice)"
        })
        
        with open("sessions.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"📝 [Transcript Synced to UI] {role}: '{text[:50]}...'")
    except Exception as e:
        logger.error(f"Failed to sync transcript to sessions.json: {e}")

# ============================================================
# LiveKit Worker Entrypoint (v1.0 Architecture)
# ============================================================
async def entrypoint(ctx: JobContext):
    logger.info(f"🔗 Connecting to WebRTC Room: {ctx.room.name}")
    await ctx.connect()

    emp_id = ctx.room.name.replace("room-", "").upper() if "room-" in ctx.room.name else "EMP101"

    @function_tool
    async def consult_enterprise_backend(
        context: RunContext,
        query: str
    ) -> str:
        """Consults the EnterpriseAssist AI backend (HR, IT, Finance, Travel, Knowledge) to answer employee questions or perform actions."""
        logger.info(f"🎙️ [Voice Bridge] Query from {emp_id}: '{query}'")
        
        # 1. Log the employee's verbal question to the text chat UI
        log_to_sessions_json(emp_id, "user", query)
        
        try:
            state = {"messages": [HumanMessage(content=query)], "employee_id": emp_id}
            result = await master_graph.ainvoke(state)
            last_msg = result["messages"][-1].content
            
            clean_speech = last_msg.replace("[RENDER_LEAVE_FORM]", "I have opened the leave application form on your screen.") \
                                   .replace("[RENDER_TICKET_FORM]", "I have opened the IT ticket form on your screen.") \
                                   .replace("[RENDER_EXPENSE_FORM]", "I have opened the expense claim form on your screen.") \
                                   .replace("[RENDER_TRAVEL_FORM]", "I have opened the business travel request form on your screen.")
            
            logger.info(f"📢 [Voice Bridge] Answer: '{clean_speech[:100]}...'")
            
            # 2. Log Aiden's verbal response to the text chat UI
            log_to_sessions_json(emp_id, "assistant", clean_speech)
            return clean_speech
        except Exception as e:
            err_msg = f"I encountered a temporary error checking the enterprise database: {str(e)}"
            log_to_sessions_json(emp_id, "assistant", err_msg)
            return err_msg

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(api_key=os.getenv("DEEPGRAM_API_KEY")),
        llm=groq.LLM(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY")),
        tts=deepgram.TTS(api_key=os.getenv("DEEPGRAM_API_KEY")),
        user_away_timeout=180.0,
    )

    agent = Agent(
        instructions=(
            f"You are Aiden, the official AI voice assistant for EnterpriseAssist speaking with Employee ID '{emp_id}'.\n"
            "YOUR RULES:\n"
            "1. Always keep your verbal responses concise, friendly, and natural. Do not use complex bullet points or markdown syntax.\n"
            "2. Whenever the employee asks about HR leave, IT tickets, Finance reimbursement, Travel planning, or company rules, "
            "YOU MUST call the tool 'consult_enterprise_backend' to get the factual answer. Never invent leave balances or rules!\n"
            "3. Speak the answer clearly and professionally."
        ),
        tools=[consult_enterprise_backend],
    )

    await session.start(agent=agent, room=ctx.room)
    logger.info(f"🟢 Voice Session Started for {emp_id}")

    greeting = "Hello! I'm Aiden, your enterprise voice assistant. How can I help you today?"
    log_to_sessions_json(emp_id, "assistant", greeting)
    await session.generate_reply(instructions="Greet the user warmly as Aiden, state that you are active, and ask how you can assist them today.")

    while True:
        await asyncio.sleep(10)
        if not ctx.room.isconnected():
            logger.info("🚪 Room disconnected by user browser. Stopping worker.")
            break
        if len(ctx.room.remote_participants) == 0:
            logger.info("🕒 All participants left. Closing WebRTC voice channel.")
            await ctx.room.disconnect()
            break

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))