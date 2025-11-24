import uuid
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# --- Data Models ---

class PerceptionSnapshot(BaseModel):
    """ERORLL Snapshot: Entities, Result, Original Goal, Reasoning, Local Goal, Local Reasoning"""
    snapshot_type: Literal["user_query", "step_result"]
    entities: List[str] = Field(default_factory=list)
    result_requirement: str = ""
    original_goal_achieved: bool = False
    reasoning: str = ""
    local_goal_achieved: bool = False
    local_reasoning: str = ""
    confidence: float = 0.0
    solution_summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ToolCode(BaseModel):
    tool_name: str
    tool_arguments: Dict[str, Any]

class PlanStep(BaseModel):
    step_index: int
    description: str
    type: Literal["CODE", "CONCLUDE", "NOP"]
    code: Optional[str] = None # Raw code string
    conclusion: Optional[str] = None
    status: Literal["pending", "completed", "failed", "skipped"] = "pending"
    execution_result: Optional[str] = None
    execution_time: Optional[str] = None
    attempts: int = 0
    perception: Optional[PerceptionSnapshot] = None # Perception of this step's result

class GlobalAgentState(BaseModel):
    """The Blackboard State"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str
    final_answer: Optional[str] = None
    
    # Shared Memory
    plan_versions: List[List[PlanStep]] = Field(default_factory=list)
    current_plan_index: int = 0
    session_memory: List[Dict[str, Any]] = Field(default_factory=list) # Failure logs, etc.
    
    # Current Context
    latest_perception: Optional[PerceptionSnapshot] = None
    context_data: Dict[str, Any] = Field(default_factory=dict) # From Retriever
    
    @property
    def user_query(self) -> str:
        """Alias for original_query for backward compatibility"""
        return self.original_query


    def add_plan_version(self, steps: List[PlanStep]):
        self.plan_versions.append(steps)
        self.current_plan_index = len(self.plan_versions) - 1

    def get_current_plan(self) -> List[PlanStep]:
        if not self.plan_versions:
            return []
        return self.plan_versions[-1]

    def update_step(self, step_index: int, **kwargs):
        plan = self.get_current_plan()
        if 0 <= step_index < len(plan):
            step = plan[step_index]
            for k, v in kwargs.items():
                setattr(step, k, v)

    def log_failure(self, query: str, error: str):
        self.session_memory.append({
            "type": "failure",
            "query": query,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })

# --- Blackboard Interface ---

class Blackboard:
    def __init__(self, query: str, session_id: Optional[str] = None):
        if session_id:
            self.state = GlobalAgentState(original_query=query, session_id=session_id)
        else:
            self.state = GlobalAgentState(original_query=query)

    def update_perception(self, snapshot: PerceptionSnapshot):
        self.state.latest_perception = snapshot
        # Also log to session memory if needed
        
    def get_snapshot(self) -> Dict[str, Any]:
        return self.state.model_dump()

    def get_history_text(self) -> str:
        """Generate a readable history for the LLM context"""
        history = []
        for i, plan in enumerate(self.state.plan_versions):
            history.append(f"--- Plan Version {i} ---")
            for step in plan:
                status_icon = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
                history.append(f"Step {step.step_index} [{status_icon}]: {step.description}")
                if step.execution_result:
                    history.append(f"  Result: {step.execution_result[:200]}...")
        return "\n".join(history)
