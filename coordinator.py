import asyncio
from agent_state import Blackboard
from perception_agent import PerceptionAgent
from decision_agent import DecisionAgent
from executor_agent import ExecutorAgent
from retriever_agent import RetrieverAgent
from memory_agent import MemoryAgent
from mcp_servers.multiMCP import MultiMCP

class Coordinator:
    def __init__(self, multi_mcp: MultiMCP):
        self.multi_mcp = multi_mcp
        # Blackboard is initialized per session/query in run()

    async def run(self, query: str):
        print(f"\n🚀 Starting Coordinator for query: {query}")
        
        # 1. Initialize Blackboard
        blackboard = Blackboard(query)
        
        # 2. Initialize Agents
        perception_agent = PerceptionAgent(blackboard)
        decision_agent = DecisionAgent(blackboard)
        executor_agent = ExecutorAgent(blackboard, self.multi_mcp)
        retriever_agent = RetrieverAgent(blackboard, self.multi_mcp)
        memory_agent = MemoryAgent(blackboard)

        # 3. Initial Perception (Understand the User)
        print("\n--- 🧠 Perception (User Query) ---")
        perception = perception_agent.run(query, snapshot_type="user_query")
        print(f"Goal: {perception.result_requirement}")
        
        if perception.original_goal_achieved:
            print(f"✅ Goal Achieved immediately: {perception.solution_summary}")
            return perception.solution_summary

        # 4. Retrieve Context
        print("\n--- 🔍 Retriever ---")
        await retriever_agent.run(query)

        # 5. Initial Planning
        print("\n--- 📝 Decision (Initial Plan) ---")
        step = decision_agent.run(mode="initial")
        
        # 6. Execution Loop
        max_steps = 10
        step_count = 0
        
        while step and step_count < max_steps:
            step_count += 1
            print(f"\n--- ⚙️ Step {step.step_index} Execution ---")
            
            # Execute
            step = await executor_agent.run(step)
            
            # Check for Conclusion
            if step.type == "CONCLUDE":
                print(f"\n🎉 Final Answer: {step.conclusion}")
                return step.conclusion

            # Perception of Result
            print("\n--- 🧠 Perception (Step Result) ---")
            perception = perception_agent.run(
                raw_input=f"Step: {step.description}\nResult: {step.execution_result}", 
                snapshot_type="step_result"
            )
            
            if perception.original_goal_achieved:
                print(f"\n✅ Goal Achieved via Perception: {perception.solution_summary}")
                return perception.solution_summary

            # Replan / Next Step
            print("\n--- 📝 Decision (Next Step) ---")
            step = decision_agent.run(mode="replan")

        return "❌ Max steps reached without conclusion."
