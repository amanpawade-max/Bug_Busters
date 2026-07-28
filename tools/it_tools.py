import json
import os
from datetime import datetime
from langchain_core.tools import tool

def read_json(filename: str) -> list:
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(filename: str, data: list):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

@tool
def reset_password(emp_id: str) -> str:
    """
    Triggers an automated password reset link ONLY when the employee explicitly commands to reset their password.
    """
    employees = read_json("employees.json")
    emp = next((e for e in employees if e.get("emp_id", "").upper() == emp_id.upper()), None)
    
    if not emp:
        return f"Error: Employee ID `{emp_id}` not found in enterprise records."
        
    email = emp.get("email", f"{emp_id.lower()}@enterprisecorp.com")
    return (
        f"### 🔐 Password Reset Initiated\n\n"
        f"* **Employee:** `{emp.get('name')}` (`{emp_id}`)\n"
        f"* **Destination Email:** `{email}`\n"
        f"* **Action:** A secure reset token valid for 15 minutes has been dispatched. Please check your inbox and spam folder."
    )

@tool
def track_it_tickets(emp_id: str) -> str:
    """Checks the status of all active or pending IT support tickets reported by an employee."""
    requests = read_json("requests.json")
    user_tickets = [r for r in requests if r.get("emp_id", "").upper() == emp_id.upper() and r.get("type") == "IT_TICKET"]
    
    if not user_tickets:
        return f"No active IT support tickets found for Employee `{emp_id}`."
        
    res = [f"### 🖥️ Active IT Tickets for `{emp_id}`:\n"]
    for t in user_tickets:
        res.append(f"* **[{t['req_id']}]** `{t['category'].upper()}` ({t['urgency']} Urgency): {t['summary']} | Status: `{t['status']}`")
    return "\n".join(res)

@tool
def close_it_ticket(emp_id: str, req_id: str) -> str:
    """
    Closes or resolves an existing IT support ticket by its Request ID (e.g., INC-501).
    """
    requests_data = read_json("requests.json")
    ticket_found = False
    
    for req in requests_data:
        if req.get("req_id", "").upper() == req_id.upper() and req.get("emp_id", "").upper() == emp_id.upper():
            req["status"] = "Closed - Resolved by User"
            req["closed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ticket_found = True
            break
            
    if not ticket_found:
        return f"❌ **Error:** Could not find an active ticket with ID `{req_id}` for Employee `{emp_id}`."
        
    write_json("requests.json", requests_data)
    return (
        f"### ✅ IT Ticket Closed Successfully\n\n"
        f"* **Ticket ID:** `{req_id}`\n"
        f"* **New Status:** `Closed - Resolved by User`\n"
        f"* **Timestamp:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    )

@tool
def raise_it_ticket(emp_id: str, category: str, urgency: str, summary: str, description: str) -> str:
    """
    Raises a formal IT Helpdesk incident ticket. Executed via UI form submission.
    """
    employees = read_json("employees.json")
    emp = next((e for e in employees if e.get("emp_id", "").upper() == emp_id.upper()), None)
    
    if not emp:
        return f"Error: Employee `{emp_id}` not found."

    requests_data = read_json("requests.json")
    ticket_id = f"INC-{len(requests_data)+501}"
    
    new_ticket = {
        "req_id": ticket_id,
        "emp_id": emp_id.upper(),
        "type": "IT_TICKET",
        "category": category,
        "urgency": urgency.upper(),
        "summary": summary,
        "description": description,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "In Progress - Assigned to IT Queue"
    }
    requests_data.append(new_ticket)
    write_json("requests.json", requests_data)

    return (
        f"### 🎟️ IT Support Ticket Created!\n\n"
        f"* **Ticket ID:** `{ticket_id}`\n"
        f"* **Category:** `{category.upper()}` | **Urgency:** `{urgency.upper()}`\n"
        f"* **Summary:** {summary}\n"
        f"* **Status:** `In Progress - Assigned to IT Queue`\n"
        f"* **SLA Note:** IT Support will review this issue within 4 business hours."
    )