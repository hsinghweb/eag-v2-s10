from agent_state import Blackboard

class MemoryAgent:
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard

    def save_session_memory(self, session_id: str, session_data: dict):
        """Save the session data to a JSON file in the memory directory."""
        import json
        import os
        from pathlib import Path
        
        memory_dir = Path("memory")
        memory_dir.mkdir(exist_ok=True)
        
        file_path = memory_dir / f"session_{session_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Session memory saved to {file_path}")
        except Exception as e:
            print(f"❌ Failed to save session memory: {e}")

    async def get_relevant_memory(self, query: str) -> str:
        """
        Retrieve relevant past failures or insights.
        Uses RAG via mcp_server_2 if available, otherwise falls back to current session memory.
        """
        # Try RAG search first
        try:
            # Check if 'search_stored_documents_rag' tool is available
            # We need access to multi_mcp, but MemoryAgent currently only has blackboard.
            # Ideally, MemoryAgent should have access to MultiMCP or Coordinator should pass it.
            # For now, we'll rely on the Coordinator to pass context or use the simple implementation
            # and let the RetrieverAgent handle the RAG part which now includes memory.
            pass
        except Exception:
            pass

        # Fallback to simple session memory check
        memory = self.blackboard.state.session_memory
        if not memory:
            return "No previous failures or insights in this session."
        
        # Simple formatting
        logs = []
        for item in memory:
            if item.get("type") == "failure":
                logs.append(f"⚠️ Failed Query: {item.get('query')} -> Error: {item.get('error')}")
        
        return "\n".join(logs) if logs else "No relevant failures found in this session."
