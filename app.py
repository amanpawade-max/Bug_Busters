import os
import requests
import uuid
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

FASTAPI_URL = "http://localhost:8000"

st.set_page_config(
    page_title="EnterpriseAssist AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Navbar & Recents Thread List
st.markdown("""
    <style>
    .block-container {
        padding-top: 3rem;
    }
    .top-navbar {
        background-color: #1e293b;
        color: #ffffff;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .top-navbar h1 { margin: 0; font-size: 1.3rem; color: #ffffff !important; }
    .st-key-message_aiden [data-testid="stChatInput"],
    .st-key-message_aiden [data-testid="stChatInput"] > div,
    .st-key-voice_toggle button {
        min-height: 56px !important;
        height: 56px !important;
    }
    .st-key-voice_toggle button {
        margin-top: 0 !important;
    }
    .recent-btn {
        text-align: left !important;
        background-color: transparent !important;
        border: none !important;
        color: #334155 !important;
    }
    .video-box {
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 6px;
        margin-bottom: 10px;
        background-color: #f8fafc;
        position: relative;
    }
    .video-label {
        position: absolute;
        bottom: 10px;
        left: 10px;
        background: rgba(15, 23, 42, 0.75);
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .user-video-placeholder {
        height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #e2e8f0;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
    }
    .user-video-placeholder svg {
        width: 72px;
        height: 72px;
        fill: #94a3b8;
    }
    </style>
""", unsafe_allow_html=True)

# --- Top Header ---
st.markdown("""
    <div class="top-navbar">
        <div>
            <h1>🤖 EnterpriseAssist AI</h1>
            <span style="color: #94a3b8; font-size: 0.85rem;">Multimodal AI Workplace Assistant</span>
        </div>
        <div>
            <span style="background: #16a34a; color: white; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 0.75rem;">● ONLINE</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "active_user" not in st.session_state:
    st.session_state.active_user = "EMP101"

if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = "session_001"

# Dictionary storing message history for each thread ID
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = {
        "session_001": [
            {"role": "assistant", "content": "Hello! I am Aiden, your EnterpriseAssist AI. How can I help you today?"}
        ]
    }

# Ensure current thread exists in dictionary
if st.session_state.current_thread_id not in st.session_state.chat_threads:
    st.session_state.chat_threads[st.session_state.current_thread_id] = [
        {"role": "assistant", "content": "Hello! I am Aiden, your EnterpriseAssist AI. How can I help you today?"}
    ]

# ==================== GEMINI-STYLE CLEAN SIDEBAR ====================
with st.sidebar:
    # 1. User Persona Dropdown
    user_options = {
        "John Doe (EMP101 - Senior Dev)": "EMP101",
        "Sarah Smith (EMP102 - HR Specialist)": "EMP102"
    }
    selected_label = st.selectbox("Persona:", list(user_options.keys()), label_visibility="collapsed")
    st.session_state.active_user = user_options[selected_label]

    st.markdown(" ")
    
    # 2. New Chat Button
    if st.button("➕ New Chat", use_container_width=True):
        new_id = f"session_{uuid.uuid4().hex[:5]}"
        st.session_state.current_thread_id = new_id
        st.session_state.chat_threads[new_id] = [
            {"role": "assistant", "content": "Started a new conversation thread. How can I assist you?"}
        ]
        st.rerun()

    st.markdown("---")
    
    # 3. Gemini-Style Recents Chat List
    st.caption("Recents")
    thread_ids = list(st.session_state.chat_threads.keys())
    
    for tid in reversed(thread_ids):
        # Create a clean label for each chat
        first_msg = st.session_state.chat_threads[tid][0]["content"] if st.session_state.chat_threads[tid] else "Chat"
        is_active = (tid == st.session_state.current_thread_id)
        btn_label = f"💬 {'[Active] ' if is_active else ''}{tid}"
        
        if st.button(btn_label, key=f"btn_{tid}", use_container_width=True):
            st.session_state.current_thread_id = tid
            st.rerun()

    st.markdown("---")

    # 4. Phase 2 Proactive Engine Scanner
    if st.button("⚡ Scan Proactive Events", use_container_width=True):
        try:
            from tools.helpers import read_json
            events = read_json("events.json")
            user_events = [e for e in events if e["emp_id"] == st.session_state.active_user and e["status"] == "UNREAD"]
            if user_events:
                event = user_events[0]
                prompt = f"[PROACTIVE ALERT] Type: {event['event_type']} | Details: {event['details']} | Suggestion: {event['suggested_action']}. Please inform the employee naturally."
                res = requests.post(f"{FASTAPI_URL}/chat", json={"employee_id": st.session_state.active_user, "thread_id": st.session_state.current_thread_id, "message": prompt}).json()
                st.session_state.chat_threads[st.session_state.current_thread_id].append({"role": "assistant", "content": f"⚠️ **Proactive Alert**\n\n{res['response']}"})
                st.rerun()
            else:
                st.success("No urgent events found.")
        except Exception as e:
            st.error(f"Event scan failed: {e}")

# ==================== MAIN DASHBOARD ====================
col_video, col_chat = st.columns([1.1, 1.9], gap="medium")

# --- ZONE 1: VIDEO CALL STACK & QUICK ACTIONS ---
with col_video:
    st.markdown("##### 📽️ Live Assistant Feed")
    
    # AI Avatar Tile
    st.markdown("""
        <div class="video-box">
            <img src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80" 
                 style="width:100%; max-height: 200px; object-fit: cover; border-radius: 6px;">
            <div class="video-label">👤 Aiden</div>
        </div>
    """, unsafe_allow_html=True)

    # User Camera Section
    if st.checkbox("🎥 Enable WebRTC Camera", value=False):
        st.camera_input("User WebRTC Feed", key="user_cam", label_visibility="collapsed")
    else:
        st.markdown("""
            <div class="user-video-placeholder" aria-label="User camera is off">
                <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <circle cx="12" cy="8" r="4"></circle>
                    <path d="M4 21c0-4.42 3.58-8 8-8s8 3.58 8 8"></path>
                </svg>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### ⚡ Quick Action Forms")
    
    action_type = st.selectbox(
        "Choose Quick Action:",
        ["Select an Action...", "🌴 Apply for Leave", "💻 Raise IT Ticket", "💰 Submit Expense", "✈️ Book Travel"],
        label_visibility="collapsed"
    )
    
    form_prompt = ""
    if action_type == "🌴 Apply for Leave":
        with st.form("form_leave"):
            st.caption("🌴 **Leave Application Form**")
            l_type = st.selectbox("Leave Type:", ["Casual", "Sick", "Annual"])
            c1, c2 = st.columns(2)
            with c1:
                l_start = st.date_input("Start Date")
            with c2:
                l_end = st.date_input("End Date")
            l_reason = st.text_input("Reason:", placeholder="e.g. Medical reasons / Family visit")
            if st.form_submit_button("Submit Leave Request", use_container_width=True):
                form_prompt = f"Apply for {l_type} leave from {l_start} to {l_end} for {l_reason if l_reason else 'Personal reasons'}"

    elif action_type == "💻 Raise IT Ticket":
        with st.form("form_it"):
            st.caption("💻 **Raise IT Ticket Form**")
            t_cat = st.selectbox("Category:", ["Software", "Hardware", "Network", "Access/Permissions", "General"])
            t_prio = st.selectbox("Priority:", ["MEDIUM", "LOW", "HIGH", "URGENT"])
            t_desc = st.text_input("Issue Description:", placeholder="e.g. Laptop screen flickering")
            if st.form_submit_button("Submit IT Ticket", use_container_width=True):
                form_prompt = f"Raise an IT ticket under {t_cat} category with {t_prio} priority for: {t_desc}"

    elif action_type == "💰 Submit Expense":
        with st.form("form_expense"):
            st.caption("💰 **Expense Reimbursement Form**")
            e_cat = st.selectbox("Category:", ["Meals", "Travel", "Office Supplies", "Software License", "Other"])
            e_amt = st.number_input("Amount ($ USD):", min_value=1.0, value=50.0, step=5.0)
            e_desc = st.text_input("Description:", placeholder="e.g. Client lunch")
            if st.form_submit_button("Submit Expense Claim", use_container_width=True):
                form_prompt = f"Submit an expense claim of ${e_amt:.2f} USD for {e_cat}: {e_desc}"

    elif action_type == "✈️ Book Travel":
        with st.form("form_travel"):
            st.caption("✈️ **Business Travel Request Form**")
            tr_dest = st.text_input("Destination:", placeholder="e.g. London, UK")
            c1, c2 = st.columns(2)
            with c1:
                tr_start = st.date_input("Departure")
            with c2:
                tr_end = st.date_input("Return")
            tr_budget = st.number_input("Estimated Budget ($):", min_value=100.0, value=1500.0, step=100.0)
            if st.form_submit_button("Submit Travel Request", use_container_width=True):
                form_prompt = f"Book business travel to {tr_dest} from {tr_start} to {tr_end} with estimated budget ${tr_budget:.2f}"

# --- ZONE 2: CHAT TRANSCRIPT ---
with col_chat:
    st.markdown(f"##### 💬 Conversation ({st.session_state.current_thread_id})")
    
    current_messages = st.session_state.chat_threads[st.session_state.current_thread_id]
    
    chat_container = st.container(height=460)
    with chat_container:
        for msg in current_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                # Render dynamic approval buttons if message is a pending HITL request
                if ("Confirmation Required" in msg.get("content", "") or msg.get("awaiting_approval")) and msg == current_messages[-1]:
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Approve & Submit", key="btn_approve", type="primary", use_container_width=True):
                            form_prompt = "yes"
                    with b2:
                        if st.button("❌ Cancel Request", key="btn_cancel", use_container_width=True):
                            form_prompt = "no"

    message_col, voice_col = st.columns([9, 1], gap="small", vertical_alignment="bottom")
    with message_col:
        user_input = st.chat_input("Message Aiden...", key="message_aiden")

    with voice_col:
        voice_enabled = "livekit_token" in st.session_state
        voice_label = "🔇" if voice_enabled else "🎙️"
        voice_help = "Turn voice off" if voice_enabled else "Turn voice on"
        if st.button(voice_label, key="voice_toggle", help=voice_help, use_container_width=True):
            if voice_enabled:
                del st.session_state["livekit_token"]
            else:
                room_name = f"room-{st.session_state.active_user}"
                try:
                    res = requests.post(
                        f"{FASTAPI_URL}/get-token",
                        json={"employee_id": st.session_state.active_user, "room_name": room_name}
                    ).json()
                    st.session_state.livekit_token = res["token"]
                except Exception:
                    st.error("Voice server offline.")
            st.rerun()

    active_message = user_input or form_prompt
    if active_message:
        current_messages.append({"role": "user", "content": active_message})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(active_message)
            with st.chat_message("assistant"):
                with st.spinner("Aiden is processing..."):
                    try:
                        res = requests.post(
                            f"{FASTAPI_URL}/chat", 
                            json={
                                "employee_id": st.session_state.active_user, 
                                "thread_id": st.session_state.current_thread_id, 
                                "message": active_message
                            }
                        ).json()
                        bot_response = res.get("response", "")
                        awaiting_approval = res.get("awaiting_approval", False)
                        
                        # Format HITL confirmation messages nicely
                        if awaiting_approval and bot_response.startswith("HITL Confirmation Required"):
                            display_response = bot_response.replace(
                                "HITL Confirmation Required",
                                "\U0001f4dd **Confirmation Required**"
                            ).replace(
                                "Ready to submit",
                                "I am ready to submit the following"
                            ).replace(
                                "Do you approve submitting this? (Reply Yes or No)",
                                "**Do you approve submitting this?** (Click below or reply Yes/No)"
                            )
                        else:
                            display_response = bot_response
                        
                        st.markdown(display_response)
                        current_messages.append({"role": "assistant", "content": display_response, "awaiting_approval": awaiting_approval})
                    except Exception as e:
                        err = f"⚠️ Server Error: Ensure server.py is running. ({e})"
                        st.error(err)
                        current_messages.append({"role": "assistant", "content": err})
        st.rerun()

if "livekit_token" in st.session_state:
    room_name = f"room-{st.session_state.active_user}"
    livekit_url = os.getenv("LIVEKIT_URL", "")
    webrtc_html = f"""
        <script src="https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js"></script>
        <script>
            async function connect() {{
                const room = new LivekitClient.Room();
                await room.connect("{livekit_url}", "{st.session_state.livekit_token}");
                await room.localParticipant.enableMicrophone();
            }}
            connect();
        </script>
    """
    st.components.v1.html(webrtc_html, height=0)