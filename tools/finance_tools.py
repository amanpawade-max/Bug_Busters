import random
from langchain_core.tools import tool
from tools.helpers import read_json, write_json

@tool
def submit_expense_claim(emp_id: str, category: str, amount: float, description: str) -> str:
    """Submits an expense reimbursement claim. Requires Human-in-the-loop confirmation."""
    expenses = read_json("expenses.json")
    expense_id = f"EXP-{random.randint(4000, 9999)}"
    new_expense = {
        "expense_id": expense_id,
        "emp_id": emp_id.upper(),
        "category": category,
        "amount": amount,
        "currency": "USD",
        "description": description,
        "status": "PENDING_APPROVAL",
        "submitted_at": "2026-07-25"
    }
    expenses.append(new_expense)
    write_json("expenses.json", expenses)
    return f"Expense claim {expense_id} for ${amount:.2f} ({category}) submitted successfully! Status: PENDING_APPROVAL."

@tool
def get_reimbursement_status(emp_id: str) -> str:
    """Fetches all reimbursement claims for a given employee."""
    expenses = read_json("expenses.json")
    user_expenses = [e for e in expenses if e["emp_id"].upper() == emp_id.upper()]
    if not user_expenses:
        return f"No expense claims found for Employee ID {emp_id}."
    
    res = [f"Expense Claims for {emp_id}:"]
    for e in user_expenses:
        res.append(f"- ID: {e['expense_id']} | Category: {e['category']} | Amount: ${e['amount']} | Status: {e['status']}")
    return "\n".join(res)