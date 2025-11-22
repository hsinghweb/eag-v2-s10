from agent_state import Blackboard
from mcp_servers.multiMCP import MultiMCP

class RetrieverAgent:
    def __init__(self, blackboard: Blackboard, multi_mcp: MultiMCP):
        self.blackboard = blackboard
        self.multi_mcp = multi_mcp

    async def run(self, query: str):
        """Fetch context before planning starts."""
        print(f"🔍 Retriever: Gathering context for '{query}'...")
        
        context_results = []
        
        # 1. Try Memory Search (if available)
        try:
            # Assuming 'documents' server has 'search_stored_documents_rag'
            # We use a broad search first
            result = await self.multi_mcp.call_tool("search_stored_documents_rag", {"query": query})
            if result:
                 # Parse result if needed, for now just store raw
                 result_str = str(result)
                 context_results.append(f"Local Documents: {result_str}")
                 print(f"📄 Retrieved {len(result_str)} characters from local documents")
                 print(f"📊 Number of lines: {result_str.count(chr(10))}")
        except Exception as e:
            print(f"Retriever (Docs) Warning: {e}")

        # 2. Try Web Search (optional, if enabled)
        # try:
        #     result = await self.multi_mcp.call_tool("duckduckgo_search_results", {"query": query})
        #     if result:
        #         context_results.append(f"Web Search: {str(result)}")
        # except Exception as e:
        #     pass

        # Store in Blackboard
        self.blackboard.state.context_data["initial_retrieval"] = "\n".join(context_results)
        print(f"🔍 Retriever: Found {len(context_results)} context sources.")
