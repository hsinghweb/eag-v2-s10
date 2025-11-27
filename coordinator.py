import asyncio
from typing import Any
from agent_state import Blackboard
from agents.perception_agent import PerceptionAgent
from agents.decision_agent import DecisionAgent
from agents.executor_agent import ExecutorAgent
from agents.retriever_agent import RetrieverAgent
from agents.memory_agent import MemoryAgent
from mcp_servers.multiMCP import MultiMCP
from conversation_logger import ConversationLogger
from io_handler import IOHandler, CLIIOHandler

class Coordinator:
    def __init__(self, multi_mcp: MultiMCP, io_handler: IOHandler = None):
        self.multi_mcp = multi_mcp
        self.logger = ConversationLogger()
        self.current_session_id = None
        self.io_handler = io_handler if io_handler else CLIIOHandler()
        # Blackboard is initialized per session/query in run()

    async def get_user_feedback(self, prompt: str, data: Any = None) -> str:
        """Async wrapper for user input via IOHandler"""
        return await self.io_handler.input(prompt, data)

    async def run(self, query: str, hitl_config: dict = None):
        await self.io_handler.output("log", f"\n🚀 Starting Coordinator for query: {query}")
        await self.io_handler.output("log", f"📝 Conversation log: {self.logger.get_log_path()}")
        
        # Log user query
        self.logger.log_user_query(query)
        
        try:
            # 1. Initialize Blackboard (reuse session ID if available)
            blackboard = Blackboard(query, session_id=self.current_session_id)
            
            # Apply HITL Config if provided
            if hitl_config:
                blackboard.state.hitl_config.update(hitl_config)
                await self.io_handler.output("log", f"⚙️ HITL Configuration updated: {blackboard.state.hitl_config}")
            
            # Store the session ID for future turns
            self.current_session_id = blackboard.state.session_id
            
            # 2. Initialize Agents
            perception_agent = PerceptionAgent(blackboard)
            decision_agent = DecisionAgent(blackboard)
            executor_agent = ExecutorAgent(blackboard, self.multi_mcp)
            retriever_agent = RetrieverAgent(blackboard, self.multi_mcp)
            memory_agent = MemoryAgent(blackboard)
            
            # 3. Initialize Session Memory
            memory_agent.initialize_session(blackboard.state.session_id)
            retriever_agent.set_session_memory(memory_agent.session_memory)

            # 4. Initial Perception (Understand the User)
            await self.io_handler.output("perception", {"type": "User Query"})
            perception = perception_agent.run(query, snapshot_type="user_query")
            await self.io_handler.output("log", f"Goal: {perception.result_requirement}")
            
            # Pass ground truth requirement to blackboard for Retriever
            if perception.require_ground_truth:
                blackboard.state.context_data["require_ground_truth"] = True
                await self.io_handler.output("log", "⚠️ Perception: Ground truth required - Prioritizing local documents")
            
            # Log perception
            self.logger.log_perception("user_query", {
                "entities": perception.entities,
                "result_requirement": perception.result_requirement,
                "original_goal_achieved": perception.original_goal_achieved,
                "confidence": perception.confidence
            })
            
            # Helper to format source
            def get_source_display(source_type):
                if source_type == "session": return "Tier 1 (Session Memory)"
                if source_type == "memory": return "Tier 2 (Conversation Memory)"
                if source_type == "documents": return "Tier 3 (Local Documents)"
                if source_type == "web": return "Web Search"
                return "Reasoning/Tool"

            if perception.original_goal_achieved:
                source = blackboard.state.context_data.get("source", "unknown")
                source_display = get_source_display(source)
                await self.io_handler.output("answer", {"answer": perception.solution_summary, "source": source_display})
                self.logger.log_conclusion(perception.solution_summary)
                
                # Add to Session Memory (Tier 1)
                memory_agent.add_to_session(
                    query=query,
                    answer=perception.solution_summary,
                    confidence=perception.confidence,
                    source=source,
                    validated=True
                )
                
                # Save to Conversation Memory FAISS (Tier 2 - if high confidence)
                await memory_agent.save_successful_answer(
                    query=query,
                    answer=perception.solution_summary,
                    confidence=perception.confidence,
                    source=source,
                    goal_achieved=True,
                    session_id=blackboard.state.session_id
                )
                
                # Finalize session
                memory_agent.finalize_session()
                
                return perception.solution_summary

            # 4. Retrieve Context
            await self.io_handler.output("retrieval", {})
            await retriever_agent.run(query)
            
            # Log retrieval
            num_sources = len(blackboard.state.context_data.get("initial_retrieval", "").split("\n"))
            self.logger.log_retriever(query, num_sources)

            # 5. Initial Planning & HITL Review
            await self.io_handler.output("decision", {"mode": "Initial Plan"})
            step = decision_agent.run(mode="initial")
            
            # HITL: Plan Approval Loop
            if blackboard.state.hitl_config["require_plan_approval"]:
                while True:
                    await self.io_handler.output("plan", {
                        "step_index": step.step_index,
                        "description": step.description,
                        "code": step.code
                    })
                    
                    feedback = await self.get_user_feedback(
                        "Approve this plan? (Press Enter to Approve, or type feedback to Replan)",
                        data={"step_index": step.step_index, "description": step.description, "code": step.code}
                    )
                    
                    if not feedback.strip():
                        await self.io_handler.output("log", "✅ Plan Approved.")
                        break
                    else:
                        await self.io_handler.output("log", f"🔄 Feedback received: '{feedback}'. Replanning...")
                        blackboard.state.user_feedback.append(feedback)
                        step = decision_agent.run(mode="replan")

            # Log decision
            self.logger.log_decision("initial", [], {
                "step_index": step.step_index,
                "description": step.description,
                "type": step.type,
                "code": step.code if step.code else ""
            })
            
            # 6. Execution Loop
            max_steps = 20
            step_count = 0
            
            while step and step_count < max_steps:
                step_count += 1
                
                # HITL: Step Approval (if enabled)
                if blackboard.state.hitl_config["require_step_approval"]:
                    await self.io_handler.output("log", f"\n🛑 HITL: About to execute Step {step.step_index}: {step.description}")
                    if step.code:
                        await self.io_handler.output("log", f"   Code:\n{step.code}")
                    
                    feedback = await self.get_user_feedback(
                        "Approve execution? (Enter to Approve, 'skip' to Skip, 'stop' to Abort)",
                        data={"step_index": step.step_index, "description": step.description, "code": step.code}
                    )
                    
                    if feedback.lower().strip() == "stop":
                        await self.io_handler.output("log", "🛑 Execution Aborted by User.")
                        return "Execution Aborted by User."
                    elif feedback.lower().strip() == "skip":
                        await self.io_handler.output("log", "⏭️ Step Skipped by User.")
                        step.status = "skipped"
                        step.execution_result = "Skipped by user"
                    else:
                        # Execute
                        await self.io_handler.output("step", {
                            "step_index": step.step_index,
                            "description": step.description,
                            "code": step.code
                        })
                        step = await executor_agent.run(step)
                else:
                    # Execute normally
                    await self.io_handler.output("step", {
                        "step_index": step.step_index,
                        "description": step.description,
                        "code": step.code
                    })
                    step = await executor_agent.run(step)
                
                # Log execution
                self.logger.log_executor(
                    step.step_index,
                    step.status,
                    step.execution_result or "",
                    str(step.execution_time) if step.execution_time else ""
                )
                
                # Check for Conclusion
                if step.type == "CONCLUDE":
                    source = blackboard.state.context_data.get("source", "Reasoning/Tool")
                    source_display = get_source_display(source)
                    await self.io_handler.output("answer", {"answer": step.conclusion, "source": source_display})
                    self.logger.log_conclusion(step.conclusion)
                    
                    # Add to Session Memory (Tier 1)
                    memory_agent.add_to_session(
                        query=query,
                        answer=step.conclusion,
                        confidence=1.0, # Assumed high confidence for explicit conclusion
                        source=source,
                        validated=True
                    )
                    
                    # Finalize session (Save SessionMemoryManager)
                    memory_agent.finalize_session()
                    
                    # Save Debug Snapshot (Blackboard state)
                    memory_agent.save_debug_snapshot(blackboard.state.session_id, blackboard.get_snapshot())
                    
                    return step.conclusion

                # Check for Dynamic HITL (ASK_USER)
                if step.type == "ASK_USER":
                    await self.io_handler.output("log", f"\n❓ Agent Requesting Help: {step.description}")
                    
                    feedback = await self.get_user_feedback(
                        f"Agent Request: {step.description}",
                        data={"step_index": step.step_index, "description": step.description}
                    )
                    
                    await self.io_handler.output("log", f"🗣️ User Feedback: {feedback}")
                    blackboard.state.user_feedback.append(feedback)
                    
                    # Force Replan immediately
                    await self.io_handler.output("decision", {"mode": "Replan (User Feedback)"})
                    step = decision_agent.run(mode="replan")
                    continue

                # Perception of Result
                await self.io_handler.output("perception", {"type": "Step Result"})
                perception = perception_agent.run(
                    raw_input=f"Step: {step.description}\nResult: {step.execution_result}", 
                    snapshot_type="step_result"
                )
                
                # Log perception
                self.logger.log_perception("step_result", {
                    "entities": perception.entities,
                    "result_requirement": perception.result_requirement,
                    "original_goal_achieved": perception.original_goal_achieved,
                    "confidence": perception.confidence,
                    "solution_summary": perception.solution_summary if perception.solution_summary else ""
                })
                
                if perception.original_goal_achieved:
                    source = blackboard.state.context_data.get("source", "Reasoning/Tool")
                    source_display = get_source_display(source)
                    await self.io_handler.output("answer", {"answer": perception.solution_summary, "source": source_display})
                    self.logger.log_conclusion(perception.solution_summary)
                    
                    # Add to Session Memory (Tier 1)
                    memory_agent.add_to_session(
                        query=query,
                        answer=perception.solution_summary,
                        confidence=perception.confidence,
                        source=source,
                        validated=True
                    )
                    
                    # Save to Conversation Memory FAISS (Tier 2 - if high confidence)
                    await memory_agent.save_successful_answer(
                        query=query,
                        answer=perception.solution_summary,
                        confidence=perception.confidence,
                        source=source,
                        goal_achieved=True,
                        session_id=blackboard.state.session_id
                    )
                    
                    # Finalize session
                    memory_agent.finalize_session()
                    
                    return perception.solution_summary

                # Replan / Next Step
                await self.io_handler.output("decision", {"mode": "Next Step"})
                step = decision_agent.run(mode="replan")
                
                # Log decision
                self.logger.log_decision("replan", [], {
                    "step_index": step.step_index,
                    "description": step.description,
                    "type": step.type,
                    "code": step.code if step.code else ""
                })

            await self.io_handler.output("error", "Max steps reached without conclusion.")
            self.logger.log_conclusion("Max steps reached without conclusion.")
            
            # Do NOT save session memory for failures
            
            return "Max steps reached."

        except Exception as e:
            error_msg = str(e)
            await self.io_handler.output("error", f"Critical Error during execution: {error_msg}")
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                conclusion = "⚠️ The system is currently experiencing high traffic (Rate Limit Exceeded). Please try again in a few minutes."
            else:
                conclusion = f"⚠️ An unexpected error occurred: {error_msg}"
            
            await self.io_handler.output("answer", {"answer": conclusion, "source": "Error Handler"})
            self.logger.log_conclusion(conclusion)
            
            # Do NOT save session memory for failures
                
            return conclusion
