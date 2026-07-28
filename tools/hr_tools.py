import random
from langchain_core.tools import tool
from tools.helpers import read_json, write_json

@tool
def get_employee_profile(emp_id: str) -> str:
    """Fetch employee profile details including name, role, department, and leave balances."""
    employees = read_json("employees.json")
    for emp in employees:
        if emp["emp_id"].upper() == emp_id.upper():
            return (
                f"Employee Found: {emp['name']} ({emp['emp_id']})\n"
                f"Role: {emp['role']} | Department: {emp['department']}\n"
                f"Leave Balances: Casual: {emp['leave_balance']['casual']}, "
                f"Sick: {emp['leave_balance']['sick']}, Annual: {emp['leave_balance']['annual']}"
            )
    return f"Error: Employee ID {emp_id} not found."

@tool
def get_leave_balance(emp_id: str) -> str:
    """Checks the remaining casual, sick, and annual leave balances for a specific employee."""
    employees = read_json("employees.json")
    for emp in employees:
        if emp["emp_id"].upper() == emp_id.upper():
            balances = emp.get("leave_balance", {})
            return (
                f"Leave Balances for Employee {emp_id} ({emp['name']}):\n"
                f"- Casual Leave: {balances.get('casual', 0)} days remaining\n"
                f"- Sick Leave: {balances.get('sick', 0)} days remaining\n"
                f"- Annual Leave: {balances.get('annual', 0)} days remaining"
            )
    return f"Error: Employee ID {emp_id} not found."

@tool
def submit_leave_request(emp_id: str, leave_type: str, start_date: str, end_date: str, reason: str = "", days: int = 0) -> str:
    """Submits a formal leave request. Requires Human-in-the-loop confirmation before invocation."""
    employees = read_json("employees.json")
    emp = next((e for e in employees if e["emp_id"].upper() == emp_id.upper()), None)
    
    if not emp:
        return f"Error: Employee {emp_id} not found."

    if days <= 0:
        try:
            from datetime import datetime
            d1 = datetime.strptime(start_date, "%Y-%m-%d")
            d2 = datetime.strptime(end_date, "%Y-%m-%d")
            days = max(1, (d2 - d1).days + 1)
        except Exception:
            days = 1

    leave_type_clean = leave_type.lower()
    balances = emp.get("leave_balance", {})
    if leave_type_clean in balances and balances[leave_type_clean] < days:
        return f"Error: Insufficient {leave_type} leave balance. Available: {balances[leave_type_clean]}, Requested: {days}."

    requests = read_json("leave_requests.json")
    req_id = f"LV-{random.randint(2000, 9999)}"
    new_request = {
        "request_id": req_id,
        "emp_id": emp_id.upper(),
        "leave_type": leave_type_clean,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "status": "PENDING_MANAGER_APPROVAL",
        "reason": reason
    }
    requests.append(new_request)
    write_json("leave_requests.json", requests)

    # Deduct balance provisionally
    if leave_type_clean in emp.get("leave_balance", {}):
        emp["leave_balance"][leave_type_clean] -= days
        write_json("employees.json", employees)

    return f"Success! Leave request {req_id} submitted for {days} day(s) of {leave_type} leave from {start_date} to {end_date}. Status: PENDING_MANAGER_APPROVAL."