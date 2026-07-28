import os
import re
import json
import asyncio
import datetime
import streamlit as st
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agents.hr_agent import get_hr_agent_executor, HR_SYSTEM_PROMPT
from agents.it_agent import get_it_agent_executor, IT_SYSTEM_PROMPT
from agents.finance_agent import get_finance_agent_executor, FINANCE_SYSTEM_PROMPT
from agents.travel_agent import get_travel_agent_executor, TRAVEL_SYSTEM_PROMPT
from tools.hr_tools import submit_leave_request
from tools.it_tools import raise_it_ticket
from tools.finance_tools import submit_expense_claim
from tools.travel_tools import submit_travel_request

load_dotenv()

def extract_leaked_tool_calls(text: str) -> list:
    pattern = r"(?:<)?function=(\w+)>(.*?)</function>"
    matches = re.findall(pattern, text)
    extracted = []
    for idx, (name, args_str) in enumerate(matches):
        try:
            args = json.loads(args_str.strip())
            extracted.append({"name": name, "args": args, "id": f"call_leaked_{idx}"})
        except Exception:
            pass
    return extracted

st.set_page_config(page_title="Multi-Agent Studio - EnterpriseAssist", page_icon="🤖", layout="centered")

with st.sidebar:
    st.markdown("### 🛠️ Agent Test Studio")
    selected_mode = st.radio("Select Domain Brain to Test:", ["👨‍💼 HR Specialist", "💻 IT Support", "💸 Finance Support", "✈️ Travel Support"], index=3)
    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

@st.cache_resource
def load_hr_agent(): return get_hr_agent_executor()

@st.cache_resource
def load_it_agent(): return get_it_agent_executor()

@st.cache_resource
def load_finance_agent(): return get_finance_agent_executor()

@st.cache_resource
def load_travel_agent(): return get_travel_agent_executor()

if selected_mode == "👨‍💼 HR Specialist":
    llm_with_tools, tools_by_name = load_hr_agent()
    active_prompt = HR_SYSTEM_PROMPT
    st.markdown("## 👨‍💼 HR Specialist Studio")
elif selected_mode == "💻 IT Support":
    llm_with_tools, tools_by_name = load_it_agent()
    active_prompt = IT_SYSTEM_PROMPT
    st.markdown("## 💻 IT Support Studio")
elif selected_mode == "💸 Finance Support":
    llm_with_tools, tools_by_name = load_finance_agent()
    active_prompt = FINANCE_SYSTEM_PROMPT
    st.markdown("## 💸 Finance Support Studio")
else:
    llm_with_tools, tools_by_name = load_travel_agent()
    active_prompt = TRAVEL_SYSTEM_PROMPT
    st.markdown("## ✈️ Travel Support Studio")

st.caption(f"Currently testing isolated node: **{selected_mode}** | Guardrails & Fallbacks Active")
st.markdown("---")

if "messages" not in st.session_state or not st.session_state.messages:
    if selected_mode == "👨‍💼 HR Specialist": welcome_text = "Hello! I am your HR Specialist. Ask me about your leave or policies!"
    elif selected_mode == "💻 IT Support": welcome_text = "Hello! I am your IT Support Helpdesk. Need policy FAQs, ticket tracking, ticket closing, or to raise an issue?"
    elif selected_mode == "💸 Finance Support": welcome_text = "Hello! I am your Finance Assistant. Ask about expense policies, corporate cards, reimbursement timelines, or submit a claim!"
    else: welcome_text = "Hello! I am your Travel Assistant. Ask about flight rules, hotel rate caps, per-diems, or plan a business trip!"
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]

chat_container = st.container(height=520)

with chat_container:
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            content = msg["content"]
            
            # --- FORM 1: HR LEAVE FORM ---
            if "[RENDER_LEAVE_FORM]" in content:
                clean_text = content.replace("[RENDER_LEAVE_FORM]", "").strip()
                if clean_text: st.markdown(clean_text)
                with st.form(key=f"hr_form_{idx}", clear_on_submit=True):
                    st.markdown("#### 📝 Quick Leave Application")
                    col1, col2 = st.columns(2)
                    with col1:
                        l_type = st.selectbox("Leave Type", ["casual", "sick", "annual"])
                        s_date = st.date_input("Start Date", min_value=datetime.date.today())
                    with col2:
                        emp_id = st.text_input("Employee ID", value="EMP101", disabled=True)
                        e_date = st.date_input("End Date", min_value=datetime.date.today())
                    l_reason = st.text_input("Reason for Leave", placeholder="e.g. Family function / Medical")
                    if st.form_submit_button("🚀 Submit Request", use_container_width=True):
                        if not l_reason.strip(): st.error("Please enter a reason.")
                        else:
                            res_card = submit_leave_request.invoke({"emp_id": "EMP101", "leave_type": l_type, "start_date": str(s_date), "end_date": str(e_date), "reason": l_reason})
                            st.session_state.messages.append({"role": "assistant", "content": res_card})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()

            # --- FORM 2: IT TICKET FORM ---
            elif "[RENDER_TICKET_FORM]" in content:
                clean_text = content.replace("[RENDER_TICKET_FORM]", "").strip()
                if clean_text: st.markdown(clean_text)
                with st.form(key=f"it_form_{idx}", clear_on_submit=True):
                    st.markdown("#### 🎟️ Raise IT Support Ticket")
                    col1, col2 = st.columns(2)
                    with col1:
                        t_cat = st.selectbox("Category", ["Hardware", "Software", "Access Management", "Network"])
                        t_urgency = st.selectbox("Urgency", ["Low", "Medium", "High", "Critical"])
                    with col2:
                        emp_id = st.text_input("Employee ID", value="EMP101", disabled=True)
                        t_summary = st.text_input("Issue Summary", placeholder="e.g. Need VS Code installed / WiFi issue")
                    t_desc = st.text_area("Detailed Description", placeholder="Explain the technical issue or software request...")
                    if st.form_submit_button("🚀 Submit Ticket", use_container_width=True):
                        if not t_summary.strip() or not t_desc.strip(): st.error("Please complete summary and description.")
                        else:
                            res_card = raise_it_ticket.invoke({"emp_id": "EMP101", "category": t_cat, "urgency": t_urgency, "summary": t_summary, "description": t_desc})
                            st.session_state.messages.append({"role": "assistant", "content": res_card})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()

            # --- FORM 3: FINANCE EXPENSE FORM ---
            elif "[RENDER_EXPENSE_FORM]" in content:
                clean_text = content.replace("[RENDER_EXPENSE_FORM]", "").strip()
                if clean_text: st.markdown(clean_text)
                with st.form(key=f"fin_form_{idx}", clear_on_submit=True):
                    st.markdown("#### 💸 Submit Business Expense Claim")
                    col1, col2 = st.columns(2)
                    with col1:
                        f_name = st.text_input("Report Name", placeholder="e.g. Client Visit - London - Oct 2026")
                        f_cat = st.selectbox("Expense Category", ["Travel", "Meals & Entertainment", "Office Supplies", "Software/Subscription", "Accommodation"])
                    with col2:
                        emp_id = st.text_input("Employee ID", value="EMP101", disabled=True)
                        c1, c2 = st.columns([1, 2])
                        with c1: f_curr = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR"])
                        with c2: f_amt = st.number_input("Amount", min_value=1.0, value=50.0, step=5.0)
                    f_desc = st.text_area("Business Justification & Details", placeholder="Provide business reason and list covered items...")
                    st.caption("📎 Note: Claims over $25 USD require digital receipt attachment per Global Expense Policy.")
                    if st.form_submit_button("🚀 Submit Expense Claim", use_container_width=True):
                        if not f_name.strip() or not f_desc.strip(): st.error("Please complete report name and business justification.")
                        else:
                            res_card = submit_expense_claim.invoke({"emp_id": "EMP101", "report_name": f_name, "category": f_cat, "amount": f_amt, "currency": f_curr, "description": f_desc})
                            st.session_state.messages.append({"role": "assistant", "content": res_card})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()

            # --- FORM 4: TRAVEL REQUEST FORM ---
            elif "[RENDER_TRAVEL_FORM]" in content:
                clean_text = content.replace("[RENDER_TRAVEL_FORM]", "").strip()
                if clean_text: st.markdown(clean_text)
                with st.form(key=f"trv_form_{idx}", clear_on_submit=True):
                    st.markdown("#### ✈️ Request Business Travel Itinerary")
                    col1, col2 = st.columns(2)
                    with col1:
                        trv_dest = st.text_input("Destination City / Country", placeholder="e.g. London, UK / New York, USA")
                        trv_s_date = st.date_input("Departure Date", min_value=datetime.date.today())
                    with col2:
                        emp_id = st.text_input("Employee ID", value="EMP101", disabled=True)
                        trv_e_date = st.date_input("Return Date", min_value=datetime.date.today())
                    
                    c1, c2 = st.columns([1, 2])
                    with c1: trv_curr = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR"])
                    with c2: trv_budget = st.number_input("Estimated Total Budget", min_value=50.0, value=1200.0, step=50.0)
                    
                    trv_purpose = st.text_area("Business Purpose & Justification", placeholder="e.g. Annual Global Sales Conference / Client Onboarding")
                    st.caption("✈️ Policy Note: Flights under 6 hours must be booked in Economy. Always select corporate rates for Marriott/Hilton.")
                    if st.form_submit_button("🚀 Submit Travel Plan", use_container_width=True):
                        if not trv_dest.strip() or not trv_purpose.strip(): st.error("Please provide destination and business purpose.")
                        else:
                            res_card = submit_travel_request.invoke({"emp_id": "EMP101", "destination": trv_dest, "start_date": str(trv_s_date), "end_date": str(trv_e_date), "purpose": trv_purpose, "budget": trv_budget, "currency": trv_curr})
                            st.session_state.messages.append({"role": "assistant", "content": res_card})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()
            else:
                st.markdown(content)

# --- Chat Execution Loop ---
if user_input := st.chat_input(f"Ask {selected_mode}..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with chat_container:
        with st.chat_message("user"): st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Agent processing..."):
                try:
                    api_messages = [SystemMessage(content=active_prompt)]
                    for m in st.session_state.messages[-8:]:
                        if m["role"] == "user": api_messages.append(HumanMessage(content=m["content"]))
                        else:
                            clean_c = m["content"].replace("[RENDER_LEAVE_FORM]", "").replace("[RENDER_TICKET_FORM]", "").replace("[RENDER_EXPENSE_FORM]", "").replace("[RENDER_TRAVEL_FORM]", "").strip()
                            if clean_c: api_messages.append(AIMessage(content=clean_c))
                    
                    response = asyncio.run(llm_with_tools.ainvoke(api_messages))
                    tool_calls = response.tool_calls if hasattr(response, "tool_calls") and response.tool_calls else []
                    
                    if not tool_calls and "function=" in response.content:
                        leaked_calls = extract_leaked_tool_calls(response.content)
                        if leaked_calls:
                            tool_calls = leaked_calls
                            response = AIMessage(content="", tool_calls=tool_calls)
                    
                    if tool_calls:
                        api_messages.append(response)
                        tool_outputs_rendered = []
                        for tc in tool_calls:
                            t_name = tc["name"]
                            t_args = tc["args"]
                            t_id = tc.get("id", f"call_{t_name}")
                            
                            if t_name in tools_by_name:
                                selected_tool = tools_by_name[t_name]
                                tool_output = selected_tool.invoke(t_args)
                                tool_outputs_rendered.append(tool_output)
                                api_messages.append(ToolMessage(content=tool_output, tool_call_id=t_id))
                            else:
                                err_msg = f"Error: Tool '{t_name}' not available in {selected_mode} mode."
                                tool_outputs_rendered.append(err_msg)
                                api_messages.append(ToolMessage(content=err_msg, tool_call_id=t_id))
                        
                        final_response = asyncio.run(llm_with_tools.ainvoke(api_messages))
                        final_text = final_response.content.strip()
                        display_content = final_text if final_text and "function=" not in final_text else "\n\n".join(tool_outputs_rendered)
                        st.markdown(display_content)
                        st.session_state.messages.append({"role": "assistant", "content": display_content})
                    else:
                        if any(token in response.content for token in ["[RENDER_LEAVE_FORM]", "[RENDER_TICKET_FORM]", "[RENDER_EXPENSE_FORM]", "[RENDER_TRAVEL_FORM]"]):
                            st.session_state.messages.append({"role": "assistant", "content": response.content})
                            st.rerun()
                        else:
                            st.markdown(response.content)
                            st.session_state.messages.append({"role": "assistant", "content": response.content})
                except Exception as e:
                    err_text = f"❌ Error: {str(e)}"
                    st.error(err_text)
                    st.session_state.messages.append({"role": "assistant", "content": err_text})