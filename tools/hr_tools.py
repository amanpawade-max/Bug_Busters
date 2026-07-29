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
def get_employee_profile(emp_id: str) -> str:
    """Looks up core profile details (name, department, role) for a specific employee ID."""
    employees = read_json("employees.json")
    for emp in employees:
        if emp.get("emp_id", "").upper() == emp_id.upper():
            return f"Profile Found: **{emp.get('name')}** | Role: `{emp.get('role')}` | Dept: `{emp.get('department')}`"
    return f"Error: Employee ID '{emp_id}' not found in HR records."

@tool
def get_leave_balance(emp_id: str) -> str:
    """Checks remaining casual, sick, and annual leave balances for an employee ID."""
    employees = read_json("employees.json")
    for emp in employees:
        if emp.get("emp_id", "").upper() == emp_id.upper():
            balances = emp.get("leave_balance", {})
            return (
                f"###  Leave Balances for {emp.get('name')} (`{emp_id}`)\n\n"
                f"* 🟢 **Casual Leave:** `{balances.get('casual', 0)} days remaining`\n"
                f"* 🟡 **Sick Leave:** `{balances.get('sick', 0)} days remaining`\n"
                f"* 🔵 **Annual Leave:** `{balances.get('annual', 0)} days remaining`"
            )
    return f"Error: Leave balance for Employee ID '{emp_id}' not found."

@tool
def track_leave_requests(emp_id: str) -> str:
    """Checks the status of all pending or approved leave requests for an employee."""
    requests = read_json("requests.json")
    user_reqs = [r for r in requests if r.get("emp_id", "").upper() == emp_id.upper() and r.get("type") == "LEAVE"]
    
    if not user_reqs:
        return f"No active leave requests found for Employee `{emp_id}`."
        
    res = [f"### 📋 Active Leave Requests for `{emp_id}`:\n"]
    for r in user_reqs:
        res.append(f"* **{r['leave_type'].upper()}**: `{r['start_date']}` to `{r['end_date']}` | Status: `{r['status']}`")
    return "\n".join(res)

@tool
def submit_leave_request(emp_id: str, leave_type: str, start_date: str, end_date: str, reason: str) -> str:
    """Submits a formal leave request after validating balance quotas and checking for date overlaps."""
    employees = read_json("employees.json")
    emp = next((e for e in employees if e.get("emp_id", "").upper() == emp_id.upper()), None)
    
    if not emp:
        return f"Error: Employee `{emp_id}` not found."

    # 1. Calculate requested days and validate date format
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        requested_days = (d2 - d1).days + 1
        if requested_days <= 0:
            return "❌ **Error:** End Date must be on or after Start Date."
    except Exception:
        return "❌ **Error:** Dates must be in YYYY-MM-DD format."

    # 2. OVERLAP GUARDRAIL: Check if employee already applied for leave on these dates!
    requests_data = read_json("requests.json")
    for req in requests_data:
        if req.get("emp_id", "").upper() == emp_id.upper() and req.get("type") == "LEAVE":
            # Ignore rejected or cancelled requests
            if "rejected" in req.get("status", "").lower() or "cancelled" in req.get("status", "").lower():
                continue
            try:
                exist_d1 = datetime.strptime(req["start_date"], "%Y-%m-%d")
                exist_d2 = datetime.strptime(req["end_date"], "%Y-%m-%d")
                # Mathematical interval overlap check: max(StartA, StartB) <= min(EndA, EndB)
                if max(d1, exist_d1) <= min(d2, exist_d2):
                    return (
                        f"### ❌ Leave Request Denied (Overlapping Dates)\n\n"
                        f"* **Requested Dates:** `{start_date}` to `{end_date}`\n"
                        f"* **Conflict Found:** You already have an active `{req.get('leave_type', '').upper()}` leave request (`{req.get('req_id')}`) from `{req['start_date']}` to `{req['end_date']}`.\n"
                        f"* **Current Status:** `{req.get('status')}`\n"
                        f"* **Action:** Please select different dates or request cancellation of your existing leave."
                    )
            except Exception:
                continue

    # 3. Check Quota Balance
    l_type = leave_type.lower()
    balances = emp.get("leave_balance", {})
    available_days = balances.get(l_type, 0)

    if requested_days > available_days:
        return (
            f"### ❌ Leave Request Denied (Insufficient Balance)\n\n"
            f"* **Requested:** `{requested_days} days` of {l_type.upper()} leave\n"
            f"* **Available Quota:** `{available_days} days` remaining\n"
            f"* **Action:** Please adjust your dates or request a different leave type."
        )

    # 4. Save valid request to requests.json
    new_req = {
        "req_id": f"REQ-{len(requests_data)+101}",
        "emp_id": emp_id.upper(),
        "type": "LEAVE",
        "leave_type": l_type,
        "start_date": start_date,
        "end_date": end_date,
        "days": requested_days,
        "reason": reason,
        "status": "Pending Manager Approval"
    }
    requests_data.append(new_req)
    write_json("requests.json", requests_data)

    return (
        f"### ✅ Leave Request Submitted Successfully!\n\n"
        f"* **Request ID:** `{new_req['req_id']}`\n"
        f"* **Leave Type:** `{l_type.upper()}` (`{requested_days} days`)\n"
        f"* **Duration:** `{start_date}` to `{end_date}`\n"
        f"* **Reason:** {reason}\n"
        f"* **Status:** `Pending Manager Approval`"
    )