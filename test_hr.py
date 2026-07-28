import os
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from tools.hr_tools import get_employee_profile, get_leave_balance, submit_leave_request

load_dotenv()

# Initialize Llama-8B
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.1,
    api_key=os.getenv("GROQ_API_KEY")
)

# Bind ONLY our HR tools
HR_TOOLS = [get_employee_profile, get_leave_balance, submit_leave_request]
llm_with_tools = llm.bind_tools(HR_TOOLS)

# Notice: We completely removed the '<function=...>' negative constraint!
STRICT_HR_PROMPT = """You are the Enterprise HR Specialist for Employee ID 'EMP101'.
RULES:
1. When asked about leave balances or profile details, call the appropriate tool directly.
2. NEVER auto-execute 'submit_leave_request'! If the user says "How do I apply for leave?" or "I want to take leave", DO NOT call the tool. Answer by explaining what details you need (dates, leave type, and reason).
3. ONLY call 'submit_leave_request' if the user explicitly provided the start date, end date, leave type, and reason in their message.
"""

async def run_hr_test(test_name: str, user_query: str):
    print(f"\n--- 🧪 TEST: {test_name} ---")
    print(f"User Query: '{user_query}'")
    
    messages = [
        SystemMessage(content=STRICT_HR_PROMPT),
        HumanMessage(content=user_query)
    ]
    
    try:
        response = await llm_with_tools.ainvoke(messages)
        
        # Check if the LLM decided to call a tool or just speak
        if response.tool_calls:
            for tc in response.tool_calls:
                print(f"🤖 Agent Action -> Called Tool: [{tc['name']}] with arguments: {tc['args']}")
        else:
            print(f"🤖 Agent Response -> {response.content}")
    except Exception as e:
        print(f"❌ Test Failed with Error: {e}")

async def main():
    print("🚀 Starting HR Agent Isolation Tests...")
    
    # Test 1: Read-only tool execution
    await run_hr_test("Check Leave Balance", "How many sick days do I have left?")
    
    # Test 2: Guardrail against auto-submitting forms!
    await run_hr_test("Guardrail Test (No Auto-Submit)", "I want to apply for leave tomorrow, what should I do?")
    
    # Test 3: Valid form submission execution
    await run_hr_test("Execute Leave Submission", "Please submit casual leave for me from 2026-08-10 to 2026-08-12 because I am attending a family wedding.")

if __name__ == "__main__":
    asyncio.run(main())