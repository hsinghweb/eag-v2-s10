import asyncio
import yaml
from mcp_servers.multiMCP import MultiMCP

async def main():
    # Load Config
    with open("config/mcp_server_config.yaml", "r") as f:
        config_data = yaml.safe_load(f)
        server_configs = config_data.get("mcp_servers", [])

    # Initialize MultiMCP
    multi_mcp = MultiMCP(server_configs=server_configs)
    await multi_mcp.initialize()

    print("\n=== Testing RAG Retrieval ===")
    print("Query: 'Who is the current Prime Minister of India?'\n")
    
    # Call the RAG search tool
    result = await multi_mcp.call_tool("search_stored_documents_rag", {"query": "Who is the current Prime Minister of India?"})
    
    print(f"Result Type: {type(result)}")
    print(f"Result: {result}")
    
    # Try to extract the actual content
    if hasattr(result, 'content'):
        print(f"\nContent Type: {type(result.content)}")
        for i, content_item in enumerate(result.content):
            print(f"\nContent Item {i+1}:")
            if hasattr(content_item, 'text'):
                print(f"Text: {content_item.text}")
            else:
                print(f"Item: {content_item}")

if __name__ == "__main__":
    asyncio.run(main())
