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
def track_travel_requests(emp_id: str) -> str:
    """Checks the approval status and itinerary details of all business travel requests for an employee."""
    requests = read_json("requests.json")
    user_trips = [r for r in requests if r.get("emp_id", "").upper() == emp_id.upper() and r.get("type") == "TRAVEL"]
    
    if not user_trips:
        return f"No business travel requests found for Employee `{emp_id}`."
        
    res = [f"### ✈️ Active Travel Plans for `{emp_id}`:\n"]
    for t in user_trips:
        res.append(f"* **[{t['req_id']}]** `{t['destination']}` ({t['start_date']} to `{t['end_date']}`) | Budget: `{t['currency']} {t['budget']}` | Status: `{t['status']}`")
    return "\n".join(res)

@tool
def submit_travel_request(emp_id: str, destination: str, start_date: str, end_date: str, purpose: str, budget: float, currency: str) -> str:
    """
    Submits a formal business travel and itinerary request. Executed via UI form submission.
    """
    employees = read_json("employees.json")
    emp = next((e for e in employees if e.get("emp_id", "").upper() == emp_id.upper()), None)
    
    if not emp:
        return f"Error: Employee `{emp_id}` not found."

    # Validate dates
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        if (d2 - d1).days < 0:
            return "❌ **Error:** Return Date must be on or after Departure Date."
    except Exception:
        return "❌ **Error:** Dates must be in YYYY-MM-DD format."

    requests_data = read_json("requests.json")
    trip_id = f"TRV-{len(requests_data)+901}"
    
    new_trip = {
        "req_id": trip_id,
        "emp_id": emp_id.upper(),
        "type": "TRAVEL",
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "purpose": purpose,
        "budget": float(budget),
        "currency": currency.upper(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Submitted - Routing to Manager & Travel Desk"
    }
    requests_data.append(new_trip)
    write_json("requests.json", requests_data)

    return (
        f"### ✈️ Business Travel Request Submitted!\n\n"
        f"* **Trip ID:** `{trip_id}`\n"
        f"* **Destination:** `{destination}` (`{start_date}` to `{end_date}`)\n"
        f"* **Purpose:** {purpose}\n"
        f"* **Estimated Budget:** `{currency.upper()} {budget}`\n"
        f"* **Status:** `Submitted - Routing to Manager & Travel Desk`\n"
        f"* **Next Steps:** Once approved, your e-tickets and hotel vouchers will populate in your portal."
    )