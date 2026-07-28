import random
from langchain_core.tools import tool
from tools.helpers import read_json, write_json

@tool
def raise_it_ticket(emp_id: str, category: str, issue_description: str, priority: str = "MEDIUM") -> str:
    """Creates a new IT support ticket. Requires Human-in-the-loop confirmation."""
    tickets = read_json("tickets.json")
    ticket_id = f"INC-{random.randint(6000, 9999)}"
    new_ticket = {
        "ticket_id": ticket_id,
        "emp_id": emp_id.upper(),
        "category": category,
        "issue_description": issue_description,
        "priority": priority.upper(),
        "status": "OPEN",
        "created_at": "2026-07-25"
    }
    tickets.append(new_ticket)
    write_json("tickets.json", tickets)
    return f"IT Ticket Created Successfully! Ticket ID: {ticket_id} | Priority: {priority.upper()} | Status: OPEN."

@tool
def check_ticket_status(ticket_id: str) -> str:
    """Checks the status of an IT ticket using its Ticket ID."""
    tickets = read_json("tickets.json")
    for ticket in tickets:
        if ticket["ticket_id"].upper() == ticket_id.upper():
            return f"Ticket {ticket['ticket_id']}: {ticket['issue_description']} | Category: {ticket['category']} | Status: {ticket['status']}"
    return f"Ticket ID {ticket_id} not found."

@tool
def reset_password(emp_id: str) -> str:
    """Triggers an automated password reset link for the employee's registered email."""
    employees = read_json("employees.json")
    emp = next((e for e in employees if e["emp_id"].upper() == emp_id.upper()), None)
    if emp:
        return f"Password reset link generated and sent to {emp['email']}. Please check your email inbox to reset your password within 15 minutes."
    return f"Error: Employee {emp_id} not found."