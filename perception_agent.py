import os
import json
from typing import Dict, Any, Optional
from google import genai
from google.genai.errors import ServerError
from dotenv import load_dotenv
from agent_state import PerceptionSnapshot, Blackboard

load_dotenv()

PERCEPTION_PROMPT = """
You are the Perception Agent (The Critic) of an advanced AI system.
Your goal is to analyze the current state of the conversation and produce a structured "ERORLL" snapshot.

INPUT:
1. Snapshot Type: "user_query" or "step_result"
2. Raw Input: The user's query OR the result of the last executed step.
3. Context: Previous conversation history and memory.
4. Current Plan: The active plan (if any).

OUTPUT (JSON):
{
    "snapshot_type": "user_query" | "step_result",
    "entities": ["list", "of", "key", "entities"],
    "result_requirement": "What exactly does the user want? (Be specific)",
    "original_goal_achieved": boolean (True if the USER'S original query is fully answered),
    "reasoning": "Why is the goal achieved or not?",
    "local_goal_achieved": boolean (True if the LAST STEP was successful),
    "local_reasoning": "Why was the step successful or failed?",
    "confidence": float (0.0 to 1.0),
    "solution_summary": "A concise summary of the answer so far."
}

CRITICAL:
- If the tool output contains the answer, set original_goal_achieved=True.
- If the tool failed, set local_goal_achieved=False and explain why in local_reasoning.
- Be strict. Do not hallucinate success.
"""

class PerceptionAgent:
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        self.client = genai.Client(api_key=self.api_key)

    def run(self, raw_input: str, snapshot_type: str = "user_query") -> PerceptionSnapshot:
        history = self.blackboard.get_history_text()
        
        prompt = f"""
        {PERCEPTION_PROMPT}

        --- CONTEXT ---
        {history}

        --- CURRENT INPUT ---
        Type: {snapshot_type}
        Content: {raw_input}
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
            # Enforce type safety
            data["snapshot_type"] = snapshot_type 
            snapshot = PerceptionSnapshot(**data)
            
            # Update Blackboard
            self.blackboard.update_perception(snapshot)
            return snapshot

        except Exception as e:
            print(f"Perception Error: {e}")
            # Fallback snapshot
            return PerceptionSnapshot(
                snapshot_type=snapshot_type,
                reasoning=f"Perception failed: {str(e)}",
                confidence=0.0
            )
