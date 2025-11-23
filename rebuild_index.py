import sys
import os
from pathlib import Path

# Add current directory and mcp_servers to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "mcp_servers"))

print("Importing process_documents from mcp_servers.mcp_server_2...")
try:
    from mcp_servers.mcp_server_2 import process_documents
    print("Starting index rebuild...")
    process_documents()
    print("✅ Index rebuild complete.")
except Exception as e:
    print(f"❌ Error rebuilding index: {e}")
    import traceback
    traceback.print_exc()
