import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class ConversationLogger:
    """Logs agent conversations in JSON format similar to ai_agent_simulated_conversation.json"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.conversation: List[Dict[str, Any]] = []
        self.turn_id = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"conversation_{self.session_id}.json"
        
    def log_user_query(self, query: str):
        """Log user query"""
        entry = {
            "turn_id": self.turn_id,
            "role": "user",
            "content": {
                "query": query
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        self.conversation.append(entry)
        self.turn_id += 1
        self._save()
        
    def log_perception(self, snapshot_type: str, perception_data: Dict[str, Any]):
        """Log perception agent output"""
        entry = {
            "turn_id": self.turn_id,
            "role": "perception",
            "content": {
                "snapshot_type": snapshot_type,
                **perception_data
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        self.conversation.append(entry)
        self.turn_id += 1
        self._save()
        
    def log_retriever(self, query: str, num_sources: int, sources_preview: str = ""):
        """Log retriever agent output"""
        entry = {
            "turn_id": self.turn_id,
            "role": "retriever",
            "content": {
                "query": query,
                "num_sources": num_sources,
                "sources_preview": sources_preview[:200] if sources_preview else ""
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        self.conversation.append(entry)
        self.turn_id += 1
        self._save()
        
    def log_decision(self, plan_mode: str, plan_text: List[str], next_step: Dict[str, Any]):
        """Log decision agent output"""
        entry = {
            "turn_id": self.turn_id,
            "role": "decision",
            "content": {
                "plan_mode": plan_mode,
                "plan_text": plan_text,
                "next_step": next_step
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        self.conversation.append(entry)
        self.turn_id += 1
        self._save()
        
    def log_executor(self, step_index: int, status: str, execution_result: str, execution_time: str = ""):
        """Log executor agent output"""
        entry = {
            "turn_id": self.turn_id,
            "role": "executor",
            "content": {
                "step_index": step_index,
                "status": status,
                "execution_result": execution_result[:500],  # Truncate long results
                "execution_time": execution_time or datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        self.conversation.append(entry)
        self.turn_id += 1
        self._save()
        
    def log_conclusion(self, conclusion: str):
        """Log final conclusion"""
        entry = {
            "turn_id": self.turn_id,
            "role": "conclusion",
            "content": {
                "conclusion": conclusion
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        self.conversation.append(entry)
        self.turn_id += 1
        self._save()
        
    def _save(self):
        """Save conversation to JSON file"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save conversation log: {e}")
            
    def get_log_path(self) -> str:
        """Get the path to the current log file"""
        return str(self.log_file)
