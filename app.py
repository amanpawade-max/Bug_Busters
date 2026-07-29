import os
import re
import json
import uuid
import asyncio
import requests
import datetime
import streamlit as st
from dotenv import load_dotenv

# --- BACKEND IMPORTS RESTORED ---
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agents.graph import build_master_graph
from tools.hr_tools import submit_leave_request
from tools.it_tools import raise_it_ticket
from tools.finance_tools import submit_expense_claim
from tools.travel_tools import submit_travel_request

load_dotenv()

FASTAPI_URL = "https://bug-busters-fi1s.onrender.com"

st.set_page_config(
    page_title="EnterpriseAssist Portal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Persistent Disk Storage Helpers (sessions.json)
# ============================================================
SESSIONS_FILE = "sessions.json"

def load_all_sessions() -> dict:
    if not os.path.exists(SESSIONS_FILE):
        return {}
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_all_sessions(data: dict):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ============================================================
# Universal Tool Leak Parser & LangGraph Setup
# ============================================================
def extract_universal_tool_calls(text: str) -> list:
    extracted = []
    xml_matches = re.findall(r"(?:<)?function=(\w+)>(.*?)(?:</function>|$)", text)
    for idx, (name, args_str) in enumerate(xml_matches):
        try:
            args = json.loads(args_str.strip())
            extracted.append({"name": name, "args": args, "id": f"call_xml_{idx}"})
        except Exception: pass
        
    if not extracted:
        raw_matches = re.findall(r"(\w+)\s*(\{.*?\})", text)
        for idx, (name, args_str) in enumerate(raw_matches):
            try:
                args = json.loads(args_str.strip())
                extracted.append({"name": name, "args": args, "id": f"call_raw_{idx}"})
            except Exception: pass
    return extracted

@st.cache_resource
def get_graph(): 
    return build_master_graph()
master_graph = get_graph()

# ============================================================
# Custom CSS Stylesheet (Rich Corporate Theme)
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stHeader"] { background-color: transparent !important; }

html, body { font-family: 'Inter', sans-serif !important; color: #0F172A !important; }
[data-testid="stAppViewContainer"] { background-color: #F8FAFC !important; }
.block-container { padding: 0.2rem 2.5rem 6rem 2.5rem !important; max-width: 1500px; }

/* MAIN HEADER */
.header-card {
    background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
    padding: 16px 32px !important; border-radius: 16px !important;
    display: flex !important; justify-content: space-between !important;
    align-items: center !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    margin-bottom: 15px !important;
}
.header-title-gradient { 
    font-size: 26px !important; 
    font-weight: 800 !important; 
    background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%); 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
}
.online-pill {
    background: #F1F5F9 !important; border: 1px solid #E2E8F0 !important;
    padding: 6px 14px !important; border-radius: 999px !important; font-weight: 600 !important;
    font-size: 12px !important; color: #0F172A !important; display: flex !important;
    align-items: center !important; gap: 8px !important;
}
.pulsating-dot {
    width: 6px; height: 6px; background-color: #10B981; border-radius: 50%;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0 !important; }
[data-testid="stSidebarContent"] { background-color: #FFFFFF !important; }

[data-testid="stSidebar"] div[data-baseweb="select"] > div { 
    background: #EFF6FF !important; 
    border: 2px solid #93C5FD !important; 
    border-radius: 10px !important; 
    box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1) !important;
}

[data-testid="stSidebar"] .stButton>button {
    height: 44px; border-radius: 10px; font-weight: 600; text-align: center;
    background: #2563EB !important; color: #FFFFFF !important; border: 1px solid #1D4ED8 !important;
}
[data-testid="stSidebar"] .stButton>button:hover { background: #1D4ED8 !important; border-color: #1E3A8A !important; }

.active-session-wrapper button { background: #1E3A8A !important; border-left: 4px solid #60A5FA !important; color: #FFFFFF !important; font-weight: 600 !important; text-align: left !important; padding-left: 16px !important; }
.inactive-session-wrapper button { background: #F8FAFC !important; border: 1px solid #E2E8F0 !important; border-left: 4px solid #CBD5E1 !important; color: #334155 !important; font-weight: 500 !important; text-align: left !important; padding-left: 16px !important; }
.del-btn-wrapper button { background: #FEF2F2 !important; border: 1px solid #FECACA !important; color: #DC2626 !important; text-align: center !important; }

.card {
    background: #FFFFFF !important; border: 1px solid rgba(241, 245, 249, 0.8) !important;
    border-radius: 18px !important; padding: 24px !important;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05) !important; margin-bottom: 20px !important;
}
.card-sub { font-size: 13px; color: #64748B; margin-bottom: 15px; }

[data-testid="stChatMessage"] {
    margin-top: 4px !important; margin-bottom: 8px !important; padding: 14px 18px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important; width: fit-content !important; max-width: 85% !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    margin-left: auto !important; margin-right: 0 !important; background: #0F172A !important;
    color: #FFFFFF !important; border: none !important; border-radius: 18px 18px 4px 18px !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p { color: #FFFFFF !important; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    margin-right: auto !important; margin-left: 0 !important; background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important; border-radius: 18px 18px 18px 4px !important;
}

/* ============================================================ */
/* NEW: FLOATING PILL CHAT INPUT CSS */
/* ============================================================ */
[data-testid="stBottomBlockContainer"] {
    background: transparent !important; /* Remove solid white block */
    padding-bottom: 20px !important;
}
[data-testid="stChatInput"] { 
    background: #FFFFFF !important; 
    border: 1px solid #E2E8F0 !important; 
    border-radius: 50px !important; /* Roundish Pill */
    padding: 6px 16px !important; 
    box-shadow: 0 15px 35px rgba(15, 23, 42, 0.15) !important; /* Floating shadow */
    margin-bottom: 20px !important;
    max-width: 900px !important; /* Prevent it from being too overwhelmingly wide */
    margin-left: auto !important;
    margin-right: auto !important;
}

.ai-banner { height: 70px; border-radius: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 600; color: #0F172A; }
.ai-avatar { margin-top: -35px; display: flex; justify-content: center; margin-bottom: 18px; }
.ai-avatar img { width: 110px; height: 110px; object-fit: cover; border-radius: 999px; border: 3px solid #FFFFFF !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important; }
.listening-badge { background: #F8FAFC; color: #0F172A; border: 1px solid #E2E8F0; padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; display: inline-block; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 999px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-card">
    <div class="header-title-gradient">Enterprise Assist AI</div>
    <div class="online-pill"><div class="pulsating-dot"></div>Secure Connection</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Session & State Initialization
# ============================================================
WELCOME_MESSAGE = (
    "Hello! I'm Aiden, your Enterprise AI Assistant.\n\n"
    "I can help with HR leave balances, IT Support tickets, Finance expense claims, "
    "Business Travel itineraries, and enterprise policies.\n\n"
    "How can I assist you today?"
)

if "active_user" not in st.session_state:
    st.session_state.active_user = "EMP101"
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = "session_001"
if "autoplay_audio" not in st.session_state:
    st.session_state.autoplay_audio = None
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

# NEW LOGIC FOR WORKSPACE VIEW TOGGLE (Avoids Widget Conflict)
if "current_workspace" not in st.session_state:
    st.session_state.current_workspace = "AI Conversation Hub"

all_sessions = load_all_sessions()
user_id = st.session_state.active_user

if user_id not in all_sessions:
    all_sessions[user_id] = {
        "session_001": [{"role": "assistant", "content": WELCOME_MESSAGE, "sender": "System"}]
    }
    save_all_sessions(all_sessions)

if st.session_state.current_thread_id not in all_sessions[user_id]:
    st.session_state.current_thread_id = list(all_sessions[user_id].keys())[0]

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="padding-bottom:20px;">
        <div style="font-size:30px; font-weight:800; color:#1E3A8A; background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 2px;">Enterprise Assist AI</div>
        <div style="font-size:15px; color:#64748B; font-weight:600;">AI Workspace Uplink</div>
    </div>
    """, unsafe_allow_html=True)

    user_options = {
        "John Doe • Senior Developer": "EMP101",
        "Sarah Smith • HR Specialist": "EMP102"
    }

    selected_user_label = st.selectbox("Employee", list(user_options.keys()), label_visibility="collapsed")
    new_user_id = user_options[selected_user_label]

    if new_user_id != st.session_state.active_user:
        st.session_state.active_user = new_user_id
        if new_user_id not in all_sessions:
            all_sessions[new_user_id] = {
                "session_001": [{"role": "assistant", "content": WELCOME_MESSAGE, "sender": "System"}]
            }
            save_all_sessions(all_sessions)
        st.session_state.current_thread_id = list(all_sessions[new_user_id].keys())[0]
        st.session_state.confirm_delete_thread = None
        st.rerun()

    st.markdown("---")
    
    # Callback to handle radio changes safely
    def update_workspace_from_radio():
        st.session_state.current_workspace = st.session_state._workspace_radio

    options = ["AI Conversation Hub", "360 Employee Dashboard"]
    radio_index = options.index(st.session_state.current_workspace)

    workspace_view = st.radio(
        "Workspace View:",
        options,
        index=radio_index,
        key="_workspace_radio",
        on_change=update_workspace_from_radio
    )
    
    st.markdown("---")

    if st.button("New Conversation", use_container_width=True):
        thread_id = f"session_{uuid.uuid4().hex[:6]}"
        st.session_state.current_thread_id = thread_id
        all_sessions[user_id][thread_id] = [
            {"role": "assistant", "content": "New workspace session created. How can I assist you today?", "sender": "System"}
        ]
        st.session_state.confirm_delete_thread = None
        save_all_sessions(all_sessions)
        st.rerun()

    st.markdown("---")
    st.markdown("<div style='margin-bottom:12px; font-size: 20px; font-weight: 700; color:#0F172A;'>Recent Sessions</div>", unsafe_allow_html=True)

    for thread in reversed(list(all_sessions[user_id].keys())):
        active = (thread == st.session_state.current_thread_id)
        label = f"Session {thread.split('_')[-1]} (Active)" if active else f"Session {thread.split('_')[-1]}"

        col_btn, col_del = st.columns([5, 1.5])
        with col_btn:
            if active:
                st.markdown("<div class='active-session-wrapper'>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='inactive-session-wrapper'>", unsafe_allow_html=True)
                
            if st.button(label, key=f"thread_{thread}", use_container_width=True):
                st.session_state.current_thread_id = thread
                st.session_state.confirm_delete_thread = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_del:
            st.markdown("<div class='del-btn-wrapper'>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_{thread}", help="Delete this chat"):
                st.session_state.confirm_delete_thread = thread
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get("confirm_delete_thread") == thread:
            st.warning("Delete this chat?")
            c_yes, c_no = st.columns(2)
            with c_yes:
                if st.button("Yes", key=f"yes_{thread}", use_container_width=True):
                    del all_sessions[user_id][thread]
                    if not all_sessions[user_id]:
                        new_id = f"session_{uuid.uuid4().hex[:6]}"
                        all_sessions[user_id][new_id] = [{"role": "assistant", "content": WELCOME_MESSAGE, "sender": "System"}]
                        st.session_state.current_thread_id = new_id
                    elif st.session_state.current_thread_id == thread:
                        st.session_state.current_thread_id = list(all_sessions[user_id].keys())[0]
                    st.session_state.confirm_delete_thread = None
                    save_all_sessions(all_sessions)
                    st.rerun()
            with c_no:
                if st.button("No", key=f"no_{thread}", use_container_width=True):
                    st.session_state.confirm_delete_thread = None
                    st.rerun()

    st.markdown("---")
    
    # ----------------------------------------------------
    # Toggles the Workspace View back and forth
    # ----------------------------------------------------
    if st.button("Scan Proactive Events", use_container_width=True):
        if st.session_state.current_workspace == "AI Conversation Hub":
            st.session_state.current_workspace = "360 Employee Dashboard"
        else:
            st.session_state.current_workspace = "AI Conversation Hub"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("EnterpriseAssist AI\nVersion 2.0")

# ============================================================
# Enterprise 360 Dashboard Renderer
# ============================================================
def render_employee_dashboard(emp_id: str):
    st.markdown(f"### 📊 Enterprise 360 Dashboard (`{emp_id}`)")
    st.caption("Consolidated view of your proactive alerts, leave quotas, helpdesk tickets, and travel itineraries.")
    st.markdown("---")

    events = []
    if os.path.exists("events.json"):
        try:
            with open("events.json", "r", encoding="utf-8") as f:
                events = [e for e in json.load(f) if e.get("emp_id", "").upper() == emp_id.upper() and e.get("status") == "UNREAD"]
        except Exception: pass

    if events:
        for ev in events:
            urgency_color = "#EF4444" if ev.get("urgency") == "HIGH" else "#F59E0B"
            st.markdown(f"""
            <div style="background: #FEF2F2; border-left: 5px solid {urgency_color}; padding: 16px 20px; border-radius: 12px; margin-bottom: 20px; border-top: 1px solid #FCA5A5; border-right: 1px solid #FCA5A5; border-bottom: 1px solid #FCA5A5;">
                <div style="color: #991B1B; font-weight: 700; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                    🚨 PROACTIVE ALERT: {ev.get('title', 'Action Required')}
                </div>
                <div style="color: #7F1D1D; font-size: 14px; margin-top: 6px;">
                    {ev.get('details')}
                </div>
                <div style="margin-top: 10px; font-weight: 600; font-size: 13px; color: #991B1B; background: #FEE2E2; padding: 6px 12px; border-radius: 6px; display: inline-block;">
                    💡 Suggested Action: {ev.get('suggested_action')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; padding: 14px 20px; border-radius: 12px; margin-bottom: 20px; color: #166534; font-weight: 500; font-size: 14px;">
            ✅ No urgent proactive alerts or document expirations detected.
        </div>
        """, unsafe_allow_html=True)

    emp_data = {}
    if os.path.exists("employees.json"):
        try:
            with open("employees.json", "r", encoding="utf-8") as f:
                emp_data = next((e for e in json.load(f) if e.get("emp_id", "").upper() == emp_id.upper()), {})
        except Exception: pass

    reqs = []
    if os.path.exists("requests.json"):
        try:
            with open("requests.json", "r", encoding="utf-8") as f:
                reqs = [r for r in json.load(f) if r.get("emp_id", "").upper() == emp_id.upper()]
        except Exception: pass

    balances = emp_data.get("leave_balance", {"casual": 0, "sick": 0, "annual": 0})
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="card" style="text-align:center;"><div class="card-sub">🟢 Casual Leave</div><div style="font-size:24px; font-weight:700; color:#0F172A;">{balances.get("casual", 0)} Days</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="card" style="text-align:center;"><div class="card-sub">🟡 Sick Leave</div><div style="font-size:24px; font-weight:700; color:#0F172A;">{balances.get("sick", 0)} Days</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="card" style="text-align:center;"><div class="card-sub">🔵 Annual Leave</div><div style="font-size:24px; font-weight:700; color:#0F172A;">{balances.get("annual", 0)} Days</div></div>', unsafe_allow_html=True)

    t_leave, t_it, t_fin, t_trv = st.tabs(["📝 Leave Requests", "🎟️ IT Tickets", "💸 Expense Claims", "✈️ Travel Plans"])
    with t_leave:
        l_reqs = [r for r in reqs if r.get("type") == "LEAVE"]
        if l_reqs:
            for r in l_reqs:
                st.markdown(f"**[{r['req_id']}]** `{r['leave_type'].upper()}` Leave ({r['start_date']} to `{r['end_date']}`) — *Status:* `{r['status']}`")
                st.divider()
        else: st.caption("No active leave requests found.")
    with t_it:
        it_reqs = [r for r in reqs if r.get("type") == "IT_TICKET"]
        if it_reqs:
            for r in it_reqs:
                st.markdown(f"**[{r['req_id']}]** `{r['category'].upper()}` ({r['urgency']} Priority): {r['summary']} — *Status:* `{r['status']}`")
                st.divider()
        else: st.caption("No active IT support tickets found.")
    with t_fin:
        f_reqs = [r for r in reqs if r.get("type") == "EXPENSE"]
        if f_reqs:
            for r in f_reqs:
                st.markdown(f"**[{r['req_id']}]** `{r['category'].upper()}` - {r['report_name']}: **{r['currency']} {r['amount']}** — *Status:* `{r['status']}`")
                st.divider()
        else: st.caption("No active expense claims found.")
    with t_trv:
        trv_reqs = [r for r in reqs if r.get("type") == "TRAVEL"]
        if trv_reqs:
            for r in trv_reqs:
                st.markdown(f"**[{r['req_id']}]** Trip to **{r['destination']}** ({r['start_date']} to `{r['end_date']}`) | Budget: `{r['currency']} {r['budget']}` — *Status:* `{r['status']}`")
                st.divider()
        else: st.caption("No business travel itineraries found.")

# ============================================================
# Main Layout (Columns)
# ============================================================
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    ai_image_url = "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?w=900"
    st.markdown(f"""
    <div class="card" style="margin-bottom: 12px;">
        <div class="ai-banner">Aiden</div>
        <div class="ai-avatar"><img src="{ai_image_url}"></div>
        <div style="margin-top:10px; text-align:center;"><span class="listening-badge">Active</span></div>
    </div>
    """, unsafe_allow_html=True)

    audio_bytes = st.audio_input("🎙️ Ask a question", label_visibility="collapsed")
    
    if audio_bytes:
        current_audio_hash = hash(audio_bytes.getvalue())
        
        if st.session_state.last_audio_hash != current_audio_hash:
            st.session_state.last_audio_hash = current_audio_hash
            
            with st.spinner("Listening and analyzing voice..."):
                try:
                    files = {"audio_file": ("audio.wav", audio_bytes, "audio/wav")}
                    data = {
                        "employee_id": st.session_state.active_user,
                        "thread_id": st.session_state.current_thread_id
                    }
                    
                    res = requests.post(f"{FASTAPI_URL}/voice-chat", files=files, data=data).json()
                    
                    current_messages = all_sessions[st.session_state.active_user][st.session_state.current_thread_id]
                    current_messages.append({"role": "user", "content": res["user_text"]})
                    current_messages.append({"role": "assistant", "content": res["answer_text"], "sender": res["sender"]})
                    save_all_sessions(all_sessions)
                    
                    if res.get("audio_base64"):
                        st.session_state.autoplay_audio = res["audio_base64"]
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error("⚠️ Failed to process voice. Is server.py running?")

    # Visible Audio Playback beneath the mic (Only renders if an audio response exists)
    if st.session_state.get("autoplay_audio"):
        import base64
        b64_audio = st.session_state.autoplay_audio
        tts_audio = base64.b64decode(b64_audio)
        st.audio(tts_audio, format="audio/mp3", autoplay=True)

with right_col:
    if st.session_state.current_workspace == "360 Employee Dashboard":
        render_employee_dashboard(user_id)
    else:
        current_messages = all_sessions[user_id][st.session_state.current_thread_id]
        chat_container = st.container(height=650, border=False)

        with chat_container:
            for idx, msg in enumerate(current_messages):
                sender_badge = f" `[{msg.get('sender', 'Assistant')}]`" if msg.get("sender") and msg.get("sender") != "System" else ""
                with st.chat_message(msg["role"]):
                    content = msg["content"]
                    
                    if "[RENDER_LEAVE_FORM]" in content:
                        clean_text = content.replace("[RENDER_LEAVE_FORM]", "").strip()
                        if clean_text: st.markdown(clean_text + sender_badge)
                        with st.form(key=f"hr_form_{idx}", clear_on_submit=True):
                            st.markdown("#### 📝 Quick Leave Application")
                            c1, c2 = st.columns(2)
                            with c1:
                                l_type = st.selectbox("Leave Type", ["casual", "sick", "annual"])
                                s_date = st.date_input("Start Date", min_value=datetime.date.today())
                            with c2:
                                emp_id = st.text_input("Employee ID", value=user_id, disabled=True)
                                e_date = st.date_input("End Date", min_value=datetime.date.today())
                            l_reason = st.text_input("Reason for Leave", placeholder="e.g. Family function / Medical")
                            if st.form_submit_button("🚀 Submit Request", use_container_width=True):
                                if not l_reason.strip(): st.error("Please enter a reason.")
                                else:
                                    res_card = submit_leave_request.invoke({"emp_id": user_id, "leave_type": l_type, "start_date": str(s_date), "end_date": str(e_date), "reason": l_reason})
                                    current_messages.append({"role": "assistant", "content": res_card, "sender": "HR Specialist"})
                                    if not clean_text: current_messages.pop(idx)
                                    else: current_messages[idx]["content"] = clean_text
                                    save_all_sessions(all_sessions)
                                    st.rerun()

                    elif "[RENDER_TICKET_FORM]" in content:
                        clean_text = content.replace("[RENDER_TICKET_FORM]", "").strip()
                        if clean_text: st.markdown(clean_text + sender_badge)
                        with st.form(key=f"it_form_{idx}", clear_on_submit=True):
                            st.markdown("#### 🎟️ Raise IT Support Ticket")
                            c1, c2 = st.columns(2)
                            with c1:
                                t_cat = st.selectbox("Category", ["Hardware", "Software", "Access Management", "Network"])
                                t_urgency = st.selectbox("Urgency", ["Low", "Medium", "High", "Critical"])
                            with c2:
                                emp_id = st.text_input("Employee ID", value=user_id, disabled=True)
                                t_summary = st.text_input("Issue Summary", placeholder="e.g. Need VS Code installed / WiFi issue")
                            t_desc = st.text_area("Detailed Description", placeholder="Explain the technical issue or software request...")
                            if st.form_submit_button("🚀 Submit Ticket", use_container_width=True):
                                if not t_summary.strip() or not t_desc.strip(): st.error("Please complete summary and description.")
                                else:
                                    res_card = raise_it_ticket.invoke({"emp_id": user_id, "category": t_cat, "urgency": t_urgency, "summary": t_summary, "description": t_desc})
                                    current_messages.append({"role": "assistant", "content": res_card, "sender": "IT Support"})
                                    if not clean_text: current_messages.pop(idx)
                                    else: current_messages[idx]["content"] = clean_text
                                    save_all_sessions(all_sessions)
                                    st.rerun()

                    elif "[RENDER_EXPENSE_FORM]" in content:
                        clean_text = content.replace("[RENDER_EXPENSE_FORM]", "").strip()
                        if clean_text: st.markdown(clean_text + sender_badge)
                        with st.form(key=f"fin_form_{idx}", clear_on_submit=True):
                            st.markdown("#### 💸 Submit Business Expense Claim")
                            c1, c2 = st.columns(2)
                            with c1:
                                f_name = st.text_input("Report Name", placeholder="e.g. Client Visit - London - Oct 2026")
                                f_cat = st.selectbox("Expense Category", ["Travel", "Meals & Entertainment", "Office Supplies", "Software/Subscription", "Accommodation"])
                            with c2:
                                emp_id = st.text_input("Employee ID", value=user_id, disabled=True)
                                col_a, col_b = st.columns([1, 2])
                                with col_a: f_curr = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR"])
                                with col_b: f_amt = st.number_input("Amount", min_value=1.0, value=50.0, step=5.0)
                            f_desc = st.text_area("Business Justification & Details", placeholder="Provide business reason and list covered items...")
                            st.caption("📎 Note: Claims over $25 USD require digital receipt attachment per Global Expense Policy.")
                            if st.form_submit_button("🚀 Submit Expense Claim", use_container_width=True):
                                if not f_name.strip() or not f_desc.strip(): st.error("Please complete report name and business justification.")
                                else:
                                    res_card = submit_expense_claim.invoke({"emp_id": user_id, "report_name": f_name, "category": f_cat, "amount": f_amt, "currency": f_curr, "description": f_desc})
                                    current_messages.append({"role": "assistant", "content": res_card, "sender": "Finance Assistant"})
                                    if not clean_text: current_messages.pop(idx)
                                    else: current_messages[idx]["content"] = clean_text
                                    save_all_sessions(all_sessions)
                                    st.rerun()

                    elif "[RENDER_TRAVEL_FORM]" in content:
                        clean_text = content.replace("[RENDER_TRAVEL_FORM]", "").strip()
                        if clean_text: st.markdown(clean_text + sender_badge)
                        with st.form(key=f"trv_form_{idx}", clear_on_submit=True):
                            st.markdown("#### ✈️ Request Business Travel Itinerary")
                            c1, c2 = st.columns(2)
                            with c1:
                                trv_dest = st.text_input("Destination City / Country", placeholder="e.g. London, UK / New York, USA")
                                trv_s_date = st.date_input("Departure Date", min_value=datetime.date.today())
                            with c2:
                                emp_id = st.text_input("Employee ID", value=user_id, disabled=True)
                                trv_e_date = st.date_input("Return Date", min_value=datetime.date.today())
                            col_a, col_b = st.columns([1, 2])
                            with col_a: trv_curr = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR"])
                            with col_b: trv_budget = st.number_input("Estimated Total Budget", min_value=50.0, value=1200.0, step=50.0)
                            trv_purpose = st.text_area("Business Purpose & Justification", placeholder="e.g. Annual Global Sales Conference / Client Onboarding")
                            if st.form_submit_button("🚀 Submit Travel Plan", use_container_width=True):
                                if not trv_dest.strip() or not trv_purpose.strip(): st.error("Please provide destination and business purpose.")
                                else:
                                    res_card = submit_travel_request.invoke({"emp_id": user_id, "destination": trv_dest, "start_date": str(trv_s_date), "end_date": str(trv_e_date), "purpose": trv_purpose, "budget": trv_budget, "currency": trv_curr})
                                    current_messages.append({"role": "assistant", "content": res_card, "sender": "Travel Desk"})
                                    if not clean_text: current_messages.pop(idx)
                                    else: current_messages[idx]["content"] = clean_text
                                    save_all_sessions(all_sessions)
                                    st.rerun()
                    else:
                        st.markdown(content + sender_badge)

# ============================================================
# Text Chat Input Processing (Full-Width at Bottom!)
# ============================================================
if st.session_state.current_workspace != "360 Employee Dashboard":
    if user_input := st.chat_input("Ask Aiden anything..."):
        current_messages = all_sessions[user_id][st.session_state.current_thread_id]
        current_messages.append({"role": "user", "content": user_input})
        save_all_sessions(all_sessions)
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)
                
            with st.chat_message("assistant"):
                with st.spinner("Analyzing request & routing to specialist..."):
                    try:
                        state_messages = []
                        for m in current_messages:
                            if m["role"] == "user":
                                state_messages.append(HumanMessage(content=m["content"]))
                            elif m["role"] == "assistant" and m.get("sender") != "System":
                                state_messages.append(AIMessage(content=m["content"]))

                        graph_state = {"messages": state_messages, "employee_id": user_id}
                        result = asyncio.run(master_graph.ainvoke(graph_state))
                        
                        last_msg = result["messages"][-1]
                        sender_name = result.get("sender", "Assistant")
                        
                        current_messages.append({"role": "assistant", "content": last_msg.content, "sender": sender_name})
                        save_all_sessions(all_sessions)
                        st.rerun()
                            
                    except Exception as e:
                        err = f"Backend Processing Notice: I encountered a formatting error verifying that request. Can you please rephrase?"
                        st.error(f"System Log: {str(e)}")
                        current_messages.append({"role": "assistant", "content": err, "sender": "System"})
                        save_all_sessions(all_sessions)
                        st.rerun()
