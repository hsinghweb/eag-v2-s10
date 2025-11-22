import asyncio
import yaml
import os
from dotenv import load_dotenv
from mcp_servers.multiMCP import MultiMCP
from coordinator import Coordinator

load_dotenv()

BANNER = """
──────────────────────────────────────────────────────
🔸  Custom Multi-Agent System (EAG V2 S10)  🔸
──────────────────────────────────────────────────────
"""

async def main():
    print(BANNER)
    
    # 1. Load MCP Config
    print("🔌 Loading MCP Servers...")
    try:
        with open("config/mcp_server_config.yaml", "r") as f:
            config_data = yaml.safe_load(f)
            server_configs = config_data.get("mcp_servers", [])
    except FileNotFoundError:
        print("❌ Config file not found: config/mcp_server_config.yaml")
        return

    # 2. Initialize MultiMCP
    multi_mcp = MultiMCP(server_configs=server_configs)
    await multi_mcp.initialize()
    
    # 3. Initialize Coordinator
    coordinator = Coordinator(multi_mcp)
    
    # 4. Interactive Loop
    print("\n✅ System Ready. Type 'exit' to quit.\n")
    
    while True:
        try:
            query = input("🟢 You: ").strip()
            if not query:
                continue
            if query.lower() in {"exit", "quit"}:
                print("👋 Goodbye!")
                break
                
            await coordinator.run(query)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
