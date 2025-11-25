"""
Quick test script to debug the iterative tool call issue
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from action.executor import run_user_code
from mcp_servers.multiMCP import MultiMCP
import yaml

async def test_iterative_calls():
    print("=" * 80)
    print("TESTING ITERATIVE TOOL CALLS")
    print("=" * 80)
    
    # Load MCP config
    with open("config/mcp_server_config.yaml", "r") as f:
        config_data = yaml.safe_load(f)
        server_configs = config_data.get("mcp_servers", [])
    
    # Initialize MultiMCP
    multi_mcp = MultiMCP(server_configs=server_configs)
    await multi_mcp.initialize()
    
    print("\n" + "=" * 80)
    print("TEST 1: Simple Fibonacci (Should Work)")
    print("=" * 80)
    
    code1 = """
fib = fibonacci_numbers(6)
print(f"Fibonacci numbers: {fib}")
"""
    
    result1 = await run_user_code(code1, multi_mcp)
    print(f"\nStatus: {result1['status']}")
    print(f"Result: {result1.get('result', result1.get('error', 'N/A'))}")
    
    print("\n" + "=" * 80)
    print("TEST 2: Simple Factorial (Should Work)")
    print("=" * 80)
    
    code2 = """
fact = factorial(5)
print(f"Factorial of 5: {fact}")
"""
    
    result2 = await run_user_code(code2, multi_mcp)
    print(f"\nStatus: {result2['status']}")
    print(f"Result: {result2.get('result', result2.get('error', 'N/A'))}")
    
    print("\n" + "=" * 80)
    print("TEST 3: Iterative Calls (Currently Broken)")
    print("=" * 80)
    
    code3 = """
fib_nums = fibonacci_numbers(6)
print(f"Got Fibonacci numbers: {fib_nums}")
print(f"Type: {type(fib_nums)}")

for num in fib_nums:
    print(f"Processing num={num}, type={type(num)}")
    fact = factorial(num)
    print(f"Factorial of {num} is {fact}")
"""
    
    result3 = await run_user_code(code3, multi_mcp)
    print(f"\nStatus: {result3['status']}")
    print(f"Result: {result3.get('result', result3.get('error', 'N/A'))}")
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_iterative_calls())
