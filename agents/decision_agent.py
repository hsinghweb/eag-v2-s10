import os
import json
from typing import List, Dict, Any
from google import genai
from dotenv import load_dotenv
from agent_state import PlanStep, Blackboard, ToolCode

load_dotenv()

DECISION_PROMPT = """
You are the Decision Agent (planner + answer synthesizer).
Given the latest perception, retrieved context, and prior tool runs, decide the single most useful next action.

CRITICAL: All tools are already registered and available as Python functions. DO NOT import external libraries like duckduckgo_search, serpapi, or googlesearch. Use the registered MCP tools directly.

**DATA SOURCE PRIORITY** (ALWAYS follow this order):
1. **FIRST**: Check if the answer is in CONTEXT DATA (from retriever/memory).
   - If the user asks a follow-up question (e.g., "What is it?", "How old is he?"), the answer is almost CERTAINLY in the CONTEXT DATA from the previous turn.
   - If the context contains a clear answer to the user's question, USE IT. Do not search again.
2. **SECOND**: If not found, use `search_stored_documents_rag(query)` to search local documents
3. **LAST RESORT**: Only use `web_search(query, max_results=5)` if the information is NOT available in memory or local documents

Available Tools (call them as regular Python functions):
- Math: add(a, b), subtract(a, b), multiply(a, b), divide(a, b), power(base, exp), cbrt(x), factorial(n), remainder(a, b), sin(x), cos(x), tan(x)
- Documents: search_stored_documents_rag(query), convert_webpage_url_into_markdown(url), extract_pdf(url)
- **Web Search (TAVILY)**: web_search(query, max_results=5) - Returns structured search results from Tavily API - **USE ONLY AS LAST RESORT**
- Web Content: download_raw_html_from_url(url)
- Utility: mine(), create_thumbnail(url), strings_to_chars_to_int(strings), int_list_to_exponential_sum(numbers), fibonacci_numbers(n)

**FAILURE HANDLING (Dynamic HITL)**:
   - If the **MOST RECENT TOOL RESULT** starts with "TOOL_FAILURE" or contains "Error":
     - **MANDATORY**: You MUST output `type="ASK_USER"` to request human guidance.
     - **DO NOT RETRY**. Even if you think you can fix it (e.g. by using Python instead of a tool), you **MUST** ask the user first.
     - Set `description` to: "The tool failed. Should I try a different approach?"
     - Do NOT output `code` for `ASK_USER`.

HOW TO CALL TOOLS:
```python
# Correct - Direct function call
result = web_search(query="Who is the Prime Minister of India?", max_results=5)
print(result)

# WRONG - Do NOT import external libraries
from duckduckgo_search import ddg  # ❌ NEVER DO THIS
from serpapi import GoogleSearch   # ❌ NEVER DO THIS
```

INPUT YOU RECEIVE:
1. Perception snapshot (ERORLL) describing the goal status.
2. Context data (aggregated retrieval + memory).
3. Most recent tool result (if any).
4. Execution history.
5. Mode ("initial" or "replan").

{
  "plan_text": ["Step 1: ...", "Step 2: ..."],
  "next_step": {
    "step_index": int,
    "description": "...",
    "type": "CODE" | "CONCLUDE" | "NOP" | "ASK_USER",
    "code": "python code (only when type == CODE)",
    "conclusion": "final short answer (only when type == CONCLUDE)"
  }
}
   - **NEVER** break code into multiple steps like "Step 1: Calculate X", "Step 2: Calculate Y". Variables are **NOT shared** between steps.
   - **BAD PLAN**: 
     - Step 1: `fib = fibonacci_numbers(8)`
     - Step 2: `fact = factorial(fib[0])` (FAILS: `fib` is undefined in Step 2)
   - **GOOD PLAN**: 
     - Step 1: `fib = fibonacci_numbers(8)\nfor x in fib:\n  print(factorial(x))` (WORKS: all in one script)
4. **Variable Persistence**: Variables defined in one `CODE` step are NOT available in the next. You must re-calculate or pass values explicitly if needed. This is why combining logic into one step is crucial.
5. **Use `print()`**: Always print the final result in your code so the Response Agent can see it.
6. The Response Agent (LLM) will interpret tool results, so focus on getting the right data, not formatting.
7. Always cite which source (tool/context) you relied on inside the conclusion text.
"""

class DecisionAgent:
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)

    def run(self, mode: str = "initial") -> PlanStep:
        state = self.blackboard.state
        perception = state.latest_perception
        history = self.blackboard.get_history_text()
        context_blob = json.dumps(state.context_data, indent=2, ensure_ascii=False) if state.context_data else "None"

        recent_result = "None"
        plan = state.get_current_plan()
        if plan:
            for step in reversed(plan):
                if step.execution_result:
                    recent_result = step.execution_result
                    break
        
        prompt = f"""
        {DECISION_PROMPT}

        --- PERCEPTION ---
        {perception.model_dump_json(indent=2) if perception else "None"}

        --- CONTEXT DATA (from retriever/memory) ---
        {context_blob}

        --- MOST RECENT TOOL RESULT ---
        {recent_result}

        --- HISTORY ---
        {history}

        --- USER FEEDBACK (HITL) ---
        {json.dumps(state.user_feedback, indent=2) if state.user_feedback else "None"}

        --- MODE ---
        {mode}
        """

        try:
            from utils import generate_with_retry
            response = generate_with_retry(
                client=self.client,
                model="gemini-2.0-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text)
            
            # Update Blackboard with the full plan text (optional, for display)
            # In a real system, we might replace the whole plan, but here we just append the next step
            
            next_step_data = data["next_step"]
            step = PlanStep(**next_step_data)
            
            # If initial, create the plan version
            if mode == "initial":
                self.blackboard.state.add_plan_version([step])
            else:
                # Append to current plan
                self.blackboard.state.get_current_plan().append(step)
                
            return step

        except Exception as e:
            print(f"Decision Error: {e}")
            return PlanStep(
                step_index=-1,
                description="Decision failed",
                type="NOP",
                execution_result=str(e)
            )
