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

    print("\n--- Testing with num_results (wrong parameter) ---")
    code_wrong = """
result = await duckduckgo_search_results(query='current Prime Minister of India', num_results=5)
"""
    result_wrong = await run_user_code(code_wrong, multi_mcp)
    print(f"Status: {result_wrong['status']}")
    print(f"Error: {result_wrong.get('error', 'N/A')}")
    print(f"Result: {result_wrong.get('result', 'N/A')[:200]}")

    print("\n--- Testing with max_results (correct parameter) ---")
    code_correct = """
result = await duckduckgo_search_results(query='current Prime Minister of India', max_results=5)
"""
    result_correct = await run_user_code(code_correct, multi_mcp)
    print(f"Status: {result_correct['status']}")
    if result_correct['status'] == 'success':
        print(f"Result (first 500 chars): {result_correct.get('result', 'N/A')[:500]}")
    else:
        print(f"Error: {result_correct.get('error', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
