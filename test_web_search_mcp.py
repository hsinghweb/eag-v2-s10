import asyncio
import yaml
from mcp_servers.multiMCP import MultiMCP
from action.executor import run_user_code

async def main():
    # Load Config
    with open("config/mcp_server_config.yaml", "r") as f:
        config_data = yaml.safe_load(f)
        server_configs = config_data.get("mcp_servers", [])

    # Initialize MultiMCP
    multi_mcp = MultiMCP(server_configs=server_configs)
    await multi_mcp.initialize()

    print("\n=== Testing web_search tool via MCP ===")
    code = """
result = await web_search(query='Who is the current Prime Minister of India?', max_results=3)
print(result)
"""
    
    result = await run_user_code(code, multi_mcp)
    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"Result:\n{result.get('result', '')[:500]}")
    else:
        print(f"Error: {result.get('error', '')}")

if __name__ == "__main__":
    asyncio.run(main())
