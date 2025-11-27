import asyncio
import json
import os
import sys
import time
import argparse
import yaml
from dotenv import load_dotenv

# Add parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_servers.multiMCP import MultiMCP
from coordinator import Coordinator
import report_generator

load_dotenv()

TEST_CASES_FILE = "simulator/test_cases.json"
HISTORY_FILE = "simulator/test_history.json"

async def run_simulator(start_idx, end_idx):
    print(f"🚀 Starting Simulator (Tests {start_idx} to {end_idx})")

    # 1. Load Test Cases
    with open(TEST_CASES_FILE, "r") as f:
        all_tests = json.load(f)
    
    # Filter tests (1-based index from CLI, convert to 0-based for list slicing)
    # If end_idx is -1, run to the end
    start_pos = max(0, start_idx - 1)
    end_pos = end_idx if end_idx != -1 else len(all_tests)
    
    tests_to_run = all_tests[start_pos:end_pos]
    print(f"📋 Queued {len(tests_to_run)} tests.")

    # 2. Initialize Backend
    print("🔌 Initializing Backend...")
    try:
        with open("config/mcp_server_config.yaml", "r") as f:
            config_data = yaml.safe_load(f)
            server_configs = config_data.get("mcp_servers", [])
    except FileNotFoundError:
        print("❌ Config file not found: config/mcp_server_config.yaml")
        return

    multi_mcp = MultiMCP(server_configs=server_configs)
    await multi_mcp.initialize()
    
    # Auto-initialize FAISS indices
    from memory_utils.auto_init_indices import initialize_all_indices
    initialize_all_indices()
    
    coordinator = Coordinator(multi_mcp)
    
    # 3. Load Existing History
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []

    # 4. Run Tests
    for i, test in enumerate(tests_to_run):
        test_id = test["id"]
        query = test["query"]
        category = test["category"]
        
        print(f"\n▶️ Running Test {test_id}: {query}")
        start_time = time.time()
        
        # Run Agent
        # We disable HITL for automation
        hitl_config = {"require_plan_approval": False, "require_step_approval": False}
        
        try:
            # Run the coordinator
            await coordinator.run(query, hitl_config=hitl_config)
            
            # Read the conversation log file to extract the final answer
            log_file = coordinator.logger.get_log_path()
            final_answer = "No answer captured"
            plan = []
            
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    
                    # Find the conclusion entry
                    for entry in reversed(log_data):
                        if entry.get("role") == "conclusion":
                            final_answer = entry.get("content", {}).get("conclusion", "No answer")
                            break
                    
                    # Extract plan from decision entries
                    for entry in log_data:
                        if entry.get("role") == "decision":
                            content = entry.get("content", {})
                            next_step = content.get("next_step", {})
                            if next_step:
                                plan.append(next_step)
            
            # Extract Tool Usage from Plan
            tool_usage = []
            for step in plan:
                if step.get("type") == "CODE":
                    pass
            
            # Let's try to extract tool names from the plan description or code
            # This is a heuristic
            for step in plan:
                if step.get("type") == "CODE":
                    code = step.get("code", "")
                    # Simple check for known tools in code
                    known_tools = [t.name for t in multi_mcp.get_all_tools()]
                    for tool in known_tools:
                        if tool + "(" in code:
                            status = "success" if step.get("status") == "completed" else "failure"
                            tool_usage.append((tool, status))

            status = "success" if final_answer else "failure"
            
        except Exception as e:
            print(f"❌ Test Failed: {e}")
            final_answer = f"Error: {str(e)}"
            plan = []
            tool_usage = []
            status = "error"

        duration = time.time() - start_time
        
        # Create Result Entry
        result_entry = {
            "id": test_id,
            "category": category,
            "query": query,
            "plan": plan,
            "result": final_answer,
            "status": status,
            "duration": duration,
            "tool_usage": tool_usage,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Update History (Overwrite if ID exists)
        # Remove existing entry with same ID if any
        history = [h for h in history if h["id"] != test_id]
        history.append(result_entry)
        
        # Save History immediately
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            
        print(f"✅ Test {test_id} Complete. Duration: {duration:.2f}s")
        
        # Sleep to avoid rate limits
        print("💤 Sleeping 10s...")
        time.sleep(10)

    # Generate Reports ONCE after all tests complete
    print("\n📊 Generating HTML Reports...")
    report_generator.generate_reports(HISTORY_FILE, "simulator")
    
    print("\n🏁 Simulator Run Complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EAG-V2 Test Simulator")
    parser.add_argument("--start", type=int, default=1, help="Start Test ID")
    parser.add_argument("--end", type=int, default=-1, help="End Test ID")
    
    args = parser.parse_args()
    
    asyncio.run(run_simulator(args.start, args.end))
