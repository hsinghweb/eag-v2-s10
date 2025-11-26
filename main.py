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
    
    # 2.5. Auto-initialize FAISS indices if they don't exist
    from memory_utils.auto_init_indices import initialize_all_indices
    initialize_all_indices()
    
    # 3. Initialize Coordinator
    coordinator = Coordinator(multi_mcp)
    
    # Try to load previous session ID
    session_file = ".last_session_id"
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                last_session_id = f.read().strip()
                if last_session_id:
                    coordinator.current_session_id = last_session_id
                    print(f"🔄 Resumed session: {last_session_id}")
        except Exception as e:
            print(f"⚠️ Failed to load last session: {e}")
    
    # 4. Interactive Loop
    print("\n✅ System Ready. Type 'exit' to quit.\n")
    
    # HITL Configuration (Default)
    hitl_config = {"require_plan_approval": True, "require_step_approval": False}
    
    while True:
        try:
            query = input("🟢 You: ").strip()
            if not query:
                continue
                
            # HITL Control Commands
            if query.lower() == "/hitl on":
                hitl_config["require_plan_approval"] = True
                print("⚙️ HITL Plan Approval ENABLED")
                continue
            elif query.lower() == "/hitl off":
                hitl_config["require_plan_approval"] = False
                print("⚙️ HITL Plan Approval DISABLED")
                continue
            elif query.lower() == "/step on":
                hitl_config["require_step_approval"] = True
                print("⚙️ HITL Step Approval ENABLED")
                continue
            elif query.lower() == "/step off":
                hitl_config["require_step_approval"] = False
                print("⚙️ HITL Step Approval DISABLED")
                continue
            elif query.lower() == "/hitl status":
                print(f"⚙️ Current HITL Config: {hitl_config}")
                continue
                
            if query.lower() in {"exit", "quit"}:
                print("👋 Goodbye!")
                break
                
            await coordinator.run(query, hitl_config=hitl_config)
            
            # Save session ID after every turn
            if coordinator.current_session_id:
                with open(session_file, "w") as f:
                    f.write(coordinator.current_session_id)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
