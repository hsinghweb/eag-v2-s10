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

    print("\n--- Testing Executor with duckduckgo_search_results ---")
    
    # Test Case 1: Direct call (Correct usage)
    code_1 = """
result = await duckduckgo_search_results(query='current Prime Minister of India')
print(f"Result 1: {result}")
"""
    print(f"\nExecuting Code 1:\n{code_1}")
    result_1 = await run_user_code(code_1, multi_mcp)
    print(f"Output 1 Status: {result_1['status']}")
    if result_1['status'] == 'success':
        print(f"Output 1 Result: {result_1['result'][:500]}") # Truncate if too long
    else:
        print(f"Output 1 Error: {result_1.get('error')}")

    # Test Case 2: Namespaced call (Incorrect usage seen in logs)
    code_2 = """
result = await websearch.duckduckgo_search_results(query='current Prime Minister of India')
print(f"Result 2: {result}")
"""
    print(f"\nExecuting Code 2:\n{code_2}")
    result_2 = await run_user_code(code_2, multi_mcp)
    print(f"Output 2 Status: {result_2['status']}")
    if result_2['status'] == 'success':
        print(f"Output 2 Result: {result_2['result'][:500]}")
    else:
        print(f"Output 2 Error: {result_2.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
