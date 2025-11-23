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
1. **FIRST**: Check if the answer is in CONTEXT DATA (from retriever/memory) - this includes past session memory and local documents
2. **SECOND**: If not found, use `search_stored_documents_rag(query)` to search local documents
3. **LAST RESORT**: Only use `web_search(query, max_results=5)` if the information is NOT available in memory or local documents

Available Tools (call them as regular Python functions):
- Math: add(a, b), subtract(a, b), multiply(a, b), divide(a, b), power(base, exp), cbrt(x), factorial(n), remainder(a, b), sin(x), cos(x), tan(x)
- Documents: search_stored_documents_rag(query), convert_webpage_url_into_markdown(url), extract_pdf(url)
- **Web Search (TAVILY)**: web_search(query, max_results=5) - Returns structured search results from Tavily API - **USE ONLY AS LAST RESORT**
- Web Content: download_raw_html_from_url(url)
- Utility: mine(), create_thumbnail(url), strings_to_chars_to_int(strings), int_list_to_exponential_sum(numbers), fibonacci_numbers(n)

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

WHAT TO OUTPUT (JSON):
{
  "plan_text": ["Step 1: ...", "Step 2: ..."],
  "next_step": {
    "step_index": int,
    "description": "...",
    "type": "CODE" | "CONCLUDE" | "NOP",
    "code": "python code (only when type == CODE)",
    "conclusion": "final short answer (only when type == CONCLUDE)"
  }
}

PRINCIPLES:
1. **ALWAYS check CONTEXT DATA first** - if the answer is there, use `type="CONCLUDE"` immediately. Do NOT call web_search if the answer is already in context.
2. Prefer `type="CONCLUDE"` as soon as the answer is explicitly present in context_data or the most recent tool result. Summarize the answer concisely (1-3 sentences) without asking the executor to parse strings.
3. Only emit `type="CODE"` when an additional tool call is absolutely required to obtain missing information. Produce minimal, self-contained Python that directly returns the needed info.
4. **For web searches, ALWAYS use web_search() function (Tavily API). NEVER import external search libraries.**
5. **Use web_search ONLY when the information is NOT in memory or local documents.**
6. The Response Agent (LLM) will interpret tool results, so focus on getting the right data, not formatting.
7. Always cite which source (tool/context) you relied on inside the conclusion text (e.g., mention the website or document name).
8. Keep `plan_text` short and focused on the remaining path to the goal.
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
