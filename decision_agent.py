import os
import json
from typing import List, Dict, Any
from google import genai
from dotenv import load_dotenv
from agent_state import PlanStep, Blackboard, ToolCode

load_dotenv()

DECISION_PROMPT = """
You are the Decision Agent (The Planner).
Your goal is to create a step-by-step plan to solve the user's query, or update the plan based on new information.

AVAILABLE TOOLS (Call these directly, DO NOT use prefixes like 'math.' or 'websearch.'):
Math Tools:
- add(a, b), subtract(a, b), multiply(a, b), divide(a, b), power(base, exponent)
- cbrt(x), factorial(n), remainder(a, b), sin(x), cos(x), tan(x)

Document Tools:
- search_stored_documents_rag(query) - Search indexed documents and memory
- convert_webpage_url_into_markdown(url) - Extract webpage content
- extract_pdf(file_path) - Convert PDF to markdown

Web Search Tools:
- web_search(query, max_results=5) - Search the web using Tavily API (NOTE: parameter is 'max_results')
- download_raw_html_from_url(url) - Fetch raw HTML

Utility Tools:
- mine(), create_thumbnail(), strings_to_chars_to_int(), int_list_to_exponential_sum(), fibonacci_numbers()

INPUT:
1. Perception Snapshot: The latest analysis of the situation.
2. History: Previous steps and results.
3. Mode: "initial" (start of task) or "replan" (after a step).

OUTPUT (JSON):
{
    "plan_text": ["Step 1: ...", "Step 2: ..."],
    "next_step": {
        "step_index": int,
        "description": "What to do next",
        "type": "CODE" | "CONCLUDE" | "NOP",
        "code": "full python code to execute (if type is CODE)",
        "conclusion": "Final answer text (if type is CONCLUDE)"
    }
}

RULES:
- Use `await` for tool calls.
- CRITICAL: Call tools DIRECTLY by name. Example: `await add(a=1, b=2)`, NOT `await math.add(...)`.
- If the goal is achieved (based on Perception), output type="CONCLUDE".
- If a step failed, try a different approach or tool.
- Keep plans concise.
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
        
        prompt = f"""
        {DECISION_PROMPT}

        --- PERCEPTION ---
        {perception.model_dump_json(indent=2) if perception else "None"}

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
