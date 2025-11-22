from agent_state import Blackboard

class MemoryAgent:
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard

    def get_relevant_memory(self, query: str) -> str:
        """
        Retrieve relevant past failures or insights.
        For now, we return all session memory (simple implementation).
        In a real system, this would use vector search.
        """
        memory = self.blackboard.state.session_memory
        if not memory:
            return "No previous failures or insights."
        
        # Simple formatting
        logs = []
        for item in memory:
            if item.get("type") == "failure":
                logs.append(f"⚠️ Failed Query: {item.get('query')} -> Error: {item.get('error')}")
        
        return "\n".join(logs) if logs else "No relevant failures found."
