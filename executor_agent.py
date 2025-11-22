import asyncio
from typing import Any, Dict
from agent_state import PlanStep, Blackboard
from action.executor import run_user_code # Reuse the safe executor logic
from mcp_servers.multiMCP import MultiMCP

class ExecutorAgent:
    def __init__(self, blackboard: Blackboard, multi_mcp: MultiMCP):
        self.blackboard = blackboard
        self.multi_mcp = multi_mcp

    async def run(self, step: PlanStep) -> PlanStep:
        """Execute a single step from the plan."""
        
        if step.type == "CODE" and step.code:
            print(f"⚡ Executing Step {step.step_index}: {step.description}")
            print(f"📝 Code ({len(step.code)} chars):\n{step.code}")
            
            # Execute the code using the safe executor
            result = await run_user_code(step.code, self.multi_mcp)
            
            # Update the step with the result
            step.execution_result = str(result.get("result", result.get("error", "Unknown Error")))
            step.execution_time = result.get("execution_time")
            
            print(f"✅ Result length: {len(step.execution_result)} characters")
            print(f"✅ Status: {result.get('status', 'unknown')}")
            
            if result.get("status") == "success":
                step.status = "completed"
            else:
                step.status = "failed"
                # Log failure to blackboard memory
                self.blackboard.state.log_failure(step.description, step.execution_result)

        elif step.type == "CONCLUDE":
            print(f"✅ Conclusion: {step.conclusion}")
            step.status = "completed"
            step.execution_result = step.conclusion
            self.blackboard.state.final_answer = step.conclusion

        elif step.type == "NOP":
            print(f"⚠️ NOP: {step.description}")
            step.status = "skipped"

        # Update the step in the blackboard
        self.blackboard.update_perception(step.perception) # If perception was pre-filled (unlikely here)
        # In reality, we update the step object which is already a reference in the blackboard
        
        return step
