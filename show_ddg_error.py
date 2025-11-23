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

    print("\n=== Testing WRONG parameter (num_results) ===")
    code_wrong = """
result = await duckduckgo_search_results(query='current Prime Minister of India', num_results=5)
"""
    result_wrong = await run_user_code(code_wrong, multi_mcp)
    print(f"Status: {result_wrong['status']}")
    if result_wrong['status'] == 'error':
        error_msg = result_wrong.get('error', '')
        print(f"Error Message ({len(error_msg)} chars): {error_msg}")
    
    print("\n=== Testing CORRECT parameter (max_results) ===")
    code_correct = """
result = await duckduckgo_search_results(query='current Prime Minister of India', max_results=5)
"""
    result_correct = await run_user_code(code_correct, multi_mcp)
    print(f"Status: {result_correct['status']}")
    if result_correct['status'] == 'success':
        result_text = result_correct.get('result', '')
        print(f"Result ({len(result_text)} chars):")
        print(result_text[:300])
    else:
        print(f"Error: {result_correct.get('error', '')}")

if __name__ == "__main__":
    asyncio.run(main())
