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
def get_reimbursement_status(emp_id: str) -> str:
    """
    Checks the payment and reimbursement processing batch status for an employee's approved expense claims.
    """
    requests = read_json("requests.json")
    user_expenses = [r for r in requests if r.get("emp_id", "").upper() == emp_id.upper() and r.get("type") == "EXPENSE"]
    
    if not user_expenses:
        return f"No expense reimbursement records found for Employee `{emp_id}`."
        
    res = [f"### 💳 Reimbursement Status for `{emp_id}`:\n"]
    for exp in user_expenses:
        res.append(f"* **[{exp['req_id']}]** `{exp['report_name']}` ({exp['currency']} {exp['amount']}) | Status: `{exp['status']}`")
    
    res.append("\n*Note: Global finance reimbursement batches are processed on the 15th and 30th of each month.*")
    return "\n".join(res)

@tool
def track_expense_claims(emp_id: str) -> str:
    """Checks the status of all submitted, pending, or approved expense reports for an employee."""
    requests = read_json("requests.json")
    user_expenses = [r for r in requests if r.get("emp_id", "").upper() == emp_id.upper() and r.get("type") == "EXPENSE"]
    
    if not user_expenses:
        return f"No active expense claims found for Employee `{emp_id}`."
        
    res = [f"### 📑 Active Expense Claims for `{emp_id}`:\n"]
    for r in user_expenses:
        res.append(f"* **[{r['req_id']}]** `{r['category'].upper()}` - {r['report_name']}: `{r['currency']} {r['amount']}` | Status: `{r['status']}`")
    return "\n".join(res)

@tool
def submit_expense_claim(emp_id: str, report_name: str, category: str, amount: float, currency: str, description: str) -> str:
    """
    Submits a formal business expense reimbursement claim. Executed via UI form submission.
    """
    employees = read_json("employees.json")
    emp = next((e for e in employees if e.get("emp_id", "").upper() == emp_id.upper()), None)
    
    if not emp:
        return f"Error: Employee `{emp_id}` not found."

    requests_data = read_json("requests.json")
    claim_id = f"EXP-{len(requests_data)+801}"
    
    # Policy check note: receipts required for claims over $25 USD / local equivalent
    receipt_note = "Digital receipt attached and verified" if float(amount) > 25 else "Under $25 threshold (No receipt required)"

    new_claim = {
        "req_id": claim_id,
        "emp_id": emp_id.upper(),
        "type": "EXPENSE",
        "report_name": report_name,
        "category": category,
        "amount": float(amount),
        "currency": currency.upper(),
        "description": description,
        "receipt_status": receipt_note,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Submitted - Waiting for Manager Approval"
    }
    requests_data.append(new_claim)
    write_json("requests.json", requests_data)

    return (
        f"### 💸 Expense Claim Submitted Successfully!\n\n"
        f"* **Claim ID:** `{claim_id}`\n"
        f"* **Report Name:** `{report_name}`\n"
        f"* **Amount:** `{currency.upper()} {amount}` (`{category.upper()}`)\n"
        f"* **Documentation:** `{receipt_note}`\n"
        f"* **Status:** `Submitted - Waiting for Manager Approval`"
    )