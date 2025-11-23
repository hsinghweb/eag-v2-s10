import asyncio
import yaml
import sys
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

    print("\n=== Testing web_search with full error capture ===\n")
    
    code = """
result = await web_search(query='Who is the current Prime Minister of India?', max_results=3)
print(f"SUCCESS: {result[:100]}...")
"""
    
    result = await run_user_code(code, multi_mcp)
    
    print(f"\n{'='*60}")
    print(f"Status: {result['status']}")
    print(f"{'='*60}")
    
    if result['status'] == 'error':
        error_msg = result.get('error', 'No error message')
        print(f"\n🔴 ERROR MESSAGE ({len(error_msg)} chars):")
        print(f"'{error_msg}'")
        print(f"\n{'='*60}")
    else:
        print(f"\n✅ SUCCESS!")
        print(f"Result: {result.get('result', '')[:200]}")

if __name__ == "__main__":
    asyncio.run(main())
