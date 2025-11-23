from agent_state import Blackboard
import faiss
import numpy as np
import json
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from utils.memory_validator import should_index_to_memory, calculate_ttl_hours
from utils.session_memory import SessionMemoryManager

# Configuration
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
ROOT = Path(__file__).parent / "mcp_servers"
MEMORY_INDEX_PATH = ROOT / "faiss_index" / "memory"

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Ollama"""
    result = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": text})
    result.raise_for_status()
    return np.array(result.json()["embedding"], dtype=np.float32)

class MemoryAgent:
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.session_memory: Optional[SessionMemoryManager] = None
    
    def initialize_session(self, session_id: str):
        """Initialize session memory for current conversation"""
        self.session_memory = SessionMemoryManager(session_id)
        print(f"[SESSION] Initialized session memory: {session_id}")
    
    def add_to_session(
        self,
        query: str,
        answer: str,
        confidence: float,
        source: str,
        validated: bool = True
    ) -> int:
        """Add turn to session memory"""
        if not self.session_memory:
            print(f"[SESSION] Warning: Session memory not initialized")
            return -1
        
        turn_id = self.session_memory.add_turn(
            query=query,
            answer=answer,
            confidence=confidence,
            source=source,
            validated=validated
        )
        
        print(f"[SESSION] Added turn {turn_id} (confidence: {confidence}, validated: {validated})")
        return turn_id
    
    def finalize_session(self):
        """Save session memory to file"""
        if self.session_memory:
            self.session_memory.save()
            print(f"[SESSION] Finalized session with {len(self.session_memory)} turns")

    async def index_to_memory_faiss(
        self,
        query: str,
        answer: str,
        confidence: float,
        source: str,
        session_id: str
    ):
        """
        Add successful answer to memory FAISS index.
        
        Args:
            query: Original user query
            answer: The answer that was generated
            confidence: Perception confidence score
            source: Source of the answer (e.g., "documents", "web_search")
            session_id: Current session ID
        """
        try:
            # Load existing index and metadata
            index_file = MEMORY_INDEX_PATH / "index.bin"
            metadata_file = MEMORY_INDEX_PATH / "metadata.json"
            
            index = faiss.read_index(str(index_file))
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            
            # Calculate TTL based on source
            ttl_hours = calculate_ttl_hours(source)
            
            # Create metadata entry
            metadata_entry = {
                "query": query,
                "answer": answer,
                "confidence": confidence,
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ttl_hours": ttl_hours,
                "session_id": session_id
            }
            
            # Get embedding for query
            query_embedding = get_embedding(query).reshape(1, -1)
            
            # Add to index
            index.add(query_embedding)
            metadata.append(metadata_entry)
            
            # Save updated index and metadata
            faiss.write_index(index, str(index_file))
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"[MEMORY] Indexed to memory FAISS:")
            print(f"  - Confidence: {confidence}")
            print(f"  - Source: {source}")
            print(f"  - TTL: {ttl_hours}h")
            print(f"  - Total vectors: {index.ntotal}")
            
        except Exception as e:
            print(f"[MEMORY] Error indexing to FAISS: {e}")

    async def save_successful_answer(
        self,
        query: str,
        answer: str,
        confidence: float,
        source: str,
        goal_achieved: bool,
        session_id: str
    ):
        """
        Save successful answer to memory FAISS if it meets criteria.
        
        Args:
            query: Original user query
            answer: The answer that was generated
            confidence: Perception confidence score
            source: Source of the answer
            goal_achieved: Whether the goal was achieved
            session_id: Current session ID
        """
        # Check if should index
        if should_index_to_memory(confidence, source, answer, goal_achieved):
            await self.index_to_memory_faiss(
                query=query,
                answer=answer,
                confidence=confidence,
                source=source,
                session_id=session_id
            )
        else:
            print(f"[MEMORY] Skipped indexing (confidence: {confidence}, source: {source})")

    def save_session_memory(self, session_id: str, session_data: dict):
        """
        Save session data to JSON file for backup/debugging.
        This is separate from FAISS indexing and used for session history.
        """
        from pathlib import Path
        
        memory_dir = Path("memory")
        memory_dir.mkdir(exist_ok=True)
        
        file_path = memory_dir / f"session_{session_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            print(f"[SESSION] Session memory saved to {file_path}")
        except Exception as e:
            print(f"[SESSION] Failed to save session memory: {e}")
