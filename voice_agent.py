import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, silero
from agents.graph import get_compiled_graph
from langchain_core.messages import HumanMessage
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceWorker")

async def entrypoint(ctx: JobContext):
    """
    Main real-time voice loop initialized when a user joins a LiveKit room.
    """
    logger.info(f"Connecting to LiveKit Room: {ctx.room.name}")
    
    # Connect and subscribe only to incoming audio streams
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected successfully! Loading LangGraph brain...")
    
    graph = await get_compiled_graph()
    
    # Extract employee ID from the room name or participant identity
    participant = await ctx.wait_for_participant()
    employee_id = participant.identity or "EMP101"
    thread_id = f"voice-{ctx.room.name}"
    config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Session started for Employee: {employee_id} | Thread: {thread_id}")

    # --- Crucial Guardrail: Instant Auto-Disconnect on User Exit ---
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(remote_participant: rtc.RemoteParticipant):
        """
        Immediately terminates the worker session if all human users leave,
        preventing background token and minute consumption.
        """
        if len(ctx.room.remote_participants) == 0:
            logger.info("🚨 All users left the room. Shutting down worker instantly to conserve free tier minutes.")
            asyncio.create_task(ctx.shutdown(drain=False))

    # Initialize Voice Activity Detection (VAD) and Speech-to-Text (STT)
    vad = silero.VAD.load()
    stt = deepgram.STT(model="nova-3", language="en")
    
    logger.info("Listening for employee speech...")
    
    # Process audio tracks from the remote participant
    for publication in participant.tracks.values():
        if publication.track and publication.track.kind == rtc.TrackKind.KIND_AUDIO:
            audio_stream = rtc.AudioStream(publication.track)
            
            # Asynchronously process transcribed speech chunks
            async def process_speech():
                async for event in stt.stream():
                    if event.type == deepgram.SpeechEventType.FINAL_TRANSCRIPT and event.alternatives:
                        spoken_text = event.alternatives[0].text.strip()
                        if not spoken_text:
                            continue
                        
                        logger.info(f"🎙️ User Spoke: '{spoken_text}'")
                        
                        # Send text into LangGraph multi-agent workflow
                        try:
                            result = await graph.ainvoke(
                                {"messages": [HumanMessage(content=spoken_text)], "employee_id": employee_id},
                                config=config
                            )
                            ai_answer = result["messages"][-1].content
                            logger.info(f"🤖 AI Response: '{ai_answer}'")
                            
                            # Push text back to UI via LiveKit Data Channel so sidebar stays synced
                            await ctx.room.local_participant.publish_data(
                                payload=ai_answer.encode("utf-8"),
                                topic="transcript"
                            )
                        except Exception as e:
                            logger.error(f"LangGraph execution error during voice turn: {e}")

            asyncio.create_task(process_speech())

if __name__ == "__main__":
    # Start the worker daemon
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))