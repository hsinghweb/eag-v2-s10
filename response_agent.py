import os
from google import genai
from dotenv import load_dotenv
from agent_state import Blackboard

load_dotenv()

RESPONSE_PROMPT = """
You are the Response Agent of an advanced AI system.

Your role is to extract the answer to the user's question from the raw tool output.

INPUT:
1. Original Question: The user's query that needs to be answered.
2. Tool Output: The raw result from an MCP tool (web search, database query, document retrieval, etc.).

OUTPUT:
A concise, direct answer to the question (1-3 sentences).

PRINCIPLES:
1. Extract the most relevant information from the tool output.
2. Cite sources when available (e.g., "According to [source]...").
3. If the answer is not in the output, respond: "The information was not found in the tool output."
4. Do not hallucinate or add information not present in the tool output.
5. Be precise and factual.

Example:
Question: "Who is the current Prime Minister of India?"
Tool Output: {"results": [{"title": "PM Modi visits...", "content": "Prime Minister Narendra Modi..."}]}
Answer: "The current Prime Minister of India is Narendra Modi."
"""

class ResponseAgent:
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self.client = genai.Client(api_key=self.api_key)
    
    def run(self, tool_result: str, question: str) -> str:
        """
        Extract answer from tool result using Gemini LLM.
        
        Args:
            tool_result: Raw output from MCP tool
            question: Original user question
            
        Returns:
            Extracted answer as a string
        """
        prompt = f"""
{RESPONSE_PROMPT}

--- QUESTION ---
{question}

--- TOOL OUTPUT ---
{tool_result}

--- YOUR ANSWER ---
"""
        
        try:
            from utils import generate_with_retry
            response = generate_with_retry(
                client=self.client,
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            answer = response.text.strip()
            
            # Store in blackboard for context
            self.blackboard.state.context_data["last_response"] = answer
            
            return answer
            
        except Exception as e:
            error_msg = f"Response Agent error: {str(e)}"
            print(f"❌ {error_msg}")
            return f"Error extracting answer: {str(e)}"
