import os
import re
import json
import asyncio
import datetime
import streamlit as st
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agents.graph import build_master_graph
from agents.hr_agent import get_hr_agent_executor, HR_SYSTEM_PROMPT
from agents.it_agent import get_it_agent_executor, IT_SYSTEM_PROMPT
from agents.finance_agent import get_finance_agent_executor, FINANCE_SYSTEM_PROMPT
from agents.travel_agent import get_travel_agent_executor, TRAVEL_SYSTEM_PROMPT
from tools.hr_tools import submit_leave_request
from tools.it_tools import raise_it_ticket
from tools.finance_tools import submit_expense_claim
from tools.travel_tools import submit_travel_request

load_dotenv()

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

st.set_page_config(page_title="EnterpriseAssist Master Studio", page_icon="🌐", layout="centered")

@st.cache_resource
def get_graph(): return build_master_graph()
master_graph = get_graph()

with st.sidebar:
    st.markdown("### 🌐 Enterprise Architecture Mode")
    selected_mode = st.radio(
        "Select Operating Mode:",
        ["🌐 Master Supervisor (All Agents)", "👨‍💼 HR Specialist", "💻 IT Support", "💸 Finance Support", "✈️ Travel Support"],
        index=0
    )
    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.markdown("## 🌐 EnterpriseAssist AI Workspace")
st.caption(f"Active Mode: **{selected_mode}** | Universal Regex Fallback Active")
st.markdown("---")

if "messages" not in st.session_state or not st.session_state.messages:
    welcome_text = "Hello! I am EnterpriseAssist. Ask me about HR leave balances, IT tickets, expense claims, or travel policies!" if selected_mode == "🌐 Master Supervisor (All Agents)" else f"Hello! Operating in isolated {selected_mode} mode. How can I help you today?"
    st.session_state.messages = [{"role": "assistant", "content": welcome_text, "sender": "System"}]

chat_container = st.container(height=520)

with chat_container:
    for idx, msg in enumerate(st.session_state.messages):
        sender_badge = f" `[{msg.get('sender', 'Assistant')}]`" if msg.get("sender") and msg.get("sender") != "System" else ""
        with st.chat_message(msg["role"]):
            content = msg["content"]
            
            if "[RENDER_LEAVE_FORM]" in content:
                clean_text = content.replace("[RENDER_LEAVE_FORM]", "").strip()
                if clean_text: st.markdown(clean_text + sender_badge)
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
                            st.session_state.messages.append({"role": "assistant", "content": res_card, "sender": "HR Specialist"})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()

            elif "[RENDER_TICKET_FORM]" in content:
                clean_text = content.replace("[RENDER_TICKET_FORM]", "").strip()
                if clean_text: st.markdown(clean_text + sender_badge)
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
                            st.session_state.messages.append({"role": "assistant", "content": res_card, "sender": "IT Support"})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()

            elif "[RENDER_EXPENSE_FORM]" in content:
                clean_text = content.replace("[RENDER_EXPENSE_FORM]", "").strip()
                if clean_text: st.markdown(clean_text + sender_badge)
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
                            st.session_state.messages.append({"role": "assistant", "content": res_card, "sender": "Finance Assistant"})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()

            elif "[RENDER_TRAVEL_FORM]" in content:
                clean_text = content.replace("[RENDER_TRAVEL_FORM]", "").strip()
                if clean_text: st.markdown(clean_text + sender_badge)
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
                            st.session_state.messages.append({"role": "assistant", "content": res_card, "sender": "Travel Desk"})
                            if not clean_text: st.session_state.messages.pop(idx)
                            else: st.session_state.messages[idx]["content"] = clean_text
                            st.rerun()
            else:
                st.markdown(content + sender_badge)

if user_input := st.chat_input("Ask EnterpriseAssist anything..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with chat_container:
        with st.chat_message("user"): st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing request & routing to specialist..."):
                try:
                    if selected_mode == "🌐 Master Supervisor (All Agents)":
                        state_messages = []
                        for m in st.session_state.messages:
                            if m["role"] == "user":
                                state_messages.append(HumanMessage(content=m["content"]))
                            elif m["role"] == "assistant" and m.get("sender") != "System":
                                state_messages.append(AIMessage(content=m["content"]))

                        graph_state = {"messages": state_messages, "employee_id": "EMP101"}
                        result = asyncio.run(master_graph.ainvoke(graph_state))
                        
                        last_msg = result["messages"][-1]
                        sender_name = result.get("sender", "Assistant")
                        
                        st.markdown(f"{last_msg.content} `[{sender_name}]`")
                        st.session_state.messages.append({"role": "assistant", "content": last_msg.content, "sender": sender_name})
                        
                        if any(tok in last_msg.content for tok in ["[RENDER_LEAVE_FORM]", "[RENDER_TICKET_FORM]", "[RENDER_EXPENSE_FORM]", "[RENDER_TRAVEL_FORM]"]):
                            st.rerun()
                            
                    else:
                        if selected_mode == "👨‍💼 HR Specialist": llm_w, t_map, p_txt = get_hr_agent_executor()[0], get_hr_agent_executor()[1], HR_SYSTEM_PROMPT
                        elif selected_mode == "💻 IT Support": llm_w, t_map, p_txt = get_it_agent_executor()[0], get_it_agent_executor()[1], IT_SYSTEM_PROMPT
                        elif selected_mode == "💸 Finance Support": llm_w, t_map, p_txt = get_finance_agent_executor()[0], get_finance_agent_executor()[1], FINANCE_SYSTEM_PROMPT
                        else: llm_w, t_map, p_txt = get_travel_agent_executor()[0], get_travel_agent_executor()[1], TRAVEL_SYSTEM_PROMPT
                        
                        api_messages = [SystemMessage(content=p_txt)]
                        for m in st.session_state.messages[-8:]:
                            if m["role"] == "user": api_messages.append(HumanMessage(content=m["content"]))
                            elif m["role"] == "assistant" and m.get("sender") != "System":
                                clean_c = m["content"].replace("[RENDER_LEAVE_FORM]", "").replace("[RENDER_TICKET_FORM]", "").replace("[RENDER_EXPENSE_FORM]", "").replace("[RENDER_TRAVEL_FORM]", "").strip()
                                if clean_c: api_messages.append(AIMessage(content=clean_c))
                                
                        response = asyncio.run(llm_w.ainvoke(api_messages))
                        tool_calls = response.tool_calls if hasattr(response, "tool_calls") and response.tool_calls else []
                        if not tool_calls and any(kw in response.content for kw in ["function=", "search_", "track_", "get_", "reset_", "close_"]):
                            leaked_calls = extract_universal_tool_calls(response.content)
                            if leaked_calls: tool_calls = leaked_calls; response = AIMessage(content="", tool_calls=tool_calls)
                            
                        if tool_calls:
                            api_messages.append(response)
                            outputs = [t_map[tc["name"]].invoke(tc["args"]) if tc["name"] in t_map else f"Error: {tc['name']} not found." for tc in tool_calls]
                            for idx, out in enumerate(outputs): api_messages.append(ToolMessage(content=out, tool_call_id=tool_calls[idx].get("id", f"id_{idx}")))
                            final_res = asyncio.run(llm_w.ainvoke(api_messages))
                            display = final_res.content.strip() if final_res.content.strip() and "function=" not in final_res.content and "{" not in final_res.content else "\n\n".join(outputs)
                            st.markdown(display)
                            st.session_state.messages.append({"role": "assistant", "content": display, "sender": selected_mode})
                        else:
                            if any(tok in response.content for tok in ["[RENDER_LEAVE_FORM]", "[RENDER_TICKET_FORM]", "[RENDER_EXPENSE_FORM]", "[RENDER_TRAVEL_FORM]"]):
                                st.session_state.messages.append({"role": "assistant", "content": response.content, "sender": selected_mode})
                                st.rerun()
                            else:
                                st.markdown(response.content)
                                st.session_state.messages.append({"role": "assistant", "content": response.content, "sender": selected_mode})
                except Exception as e:
                    err = f"❌ Error: {str(e)}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err, "sender": "System"})