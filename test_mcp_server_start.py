import subprocess
import sys

# Test if mcp_server_3.py can start at all
result = subprocess.run(
    ["uv", "run", "python", "mcp_servers/mcp_server_3.py"],
    capture_output=True,
    text=True,
    timeout=5
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
