import random
from langchain_core.tools import tool
from tools.helpers import read_json, write_json

@tool
def request_business_travel(emp_id: str, destination: str, start_date: str, end_date: str, estimated_budget: float) -> str:
    """Submits a business travel request. Requires Human-in-the-loop confirmation."""
    travels = read_json("travel_requests.json")
    travel_id = f"TRV-{random.randint(8500, 9999)}"
    new_travel = {
        "travel_id": travel_id,
        "emp_id": emp_id.upper(),
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "estimated_budget": estimated_budget,
        "status": "PENDING_TRAVEL_DESK_APPROVAL"
    }
    travels.append(new_travel)
    write_json("travel_requests.json", travels)
    return f"Travel Request {travel_id} to {destination} (${estimated_budget}) submitted! Status: PENDING_TRAVEL_DESK_APPROVAL."