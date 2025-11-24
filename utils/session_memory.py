"""
Session Memory Manager - Short-term memory for current conversation
Provides fast semantic search within the current session
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict
import requests
import numpy as np

# Configuration
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

class SessionMemoryManager:
    """
    Manages short-term memory for the current conversation session.
    Stores Q&A turns with validation flags and enables semantic search.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.conversation: List[Dict] = []
        self.file_path = Path("memory") / f"session_{session_id}.json"
    
    def add_turn(
        self,
        query: str,
        answer: str,
        confidence: float,
        source: str,
        validated: bool = True,
        context_from_turn: Optional[int] = None
    ) -> int:
        """
        Add a conversation turn to session memory.
        
        Args:
            query: User query
            answer: System answer
            confidence: Perception confidence score
            source: Source of answer (e.g., "documents", "web_search")
            validated: Whether answer passed validation
            context_from_turn: Turn ID that provided context for this turn
        
        Returns:
            int: Turn ID of added turn
        """
        turn = {
            "turn_id": len(self.conversation),
            "query": query,
            "answer": answer,
            "confidence": confidence,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validated": validated
        }
        
        if context_from_turn is not None:
            turn["context_from_turn"] = context_from_turn
        
        self.conversation.append(turn)
        return turn["turn_id"]
    
    def search_similar(
        self,
        query: str,
        threshold: float = 0.85
    ) -> Optional[Dict]:
        """
        Find most similar validated turn in current session.
        Searches both previous queries AND answers to find relevant context.
        
        Args:
            query: Query to search for
            threshold: Minimum similarity score (0.0-1.0)
        
        Returns:
            dict: Best matching turn with similarity score, or None
        """
        print(f"[SESSION_SEARCH] Searching {len(self.conversation)} turns for: '{query}'")
        best_match = None
        best_similarity = 0.0
        
        for turn in self.conversation:
            print(f"[SESSION_SEARCH] Checking turn {turn.get('turn_id')}: validated={turn.get('validated')}, confidence={turn.get('confidence')}")
            
            # Only consider validated turns
            if not turn.get("validated", False):
                print(f"[SESSION_SEARCH] Skipping turn {turn.get('turn_id')}: not validated")
                continue
            
            # Only consider high-confidence turns
            if turn.get("confidence", 0.0) < 0.9:
                print(f"[SESSION_SEARCH] Skipping turn {turn.get('turn_id')}: low confidence")
                continue
            
            # Calculate semantic similarity against BOTH query and answer
            query_similarity = self._calculate_similarity(
                query,
                turn["query"]
            )
            
            answer_similarity = self._calculate_similarity(
                query,
                turn["answer"]
            )
            
            print(f"[SESSION_SEARCH] Turn {turn.get('turn_id')}: query_sim={query_similarity:.3f}, answer_sim={answer_similarity:.3f}")
            
            # Use the higher of the two similarities
            max_similarity = max(query_similarity, answer_similarity)
            
            if max_similarity > best_similarity and max_similarity >= threshold:
                best_similarity = max_similarity
                best_match = turn.copy()
                best_match["similarity"] = max_similarity
                print(f"[SESSION_SEARCH] New best match: turn {turn.get('turn_id')} with similarity {max_similarity:.3f}")
        
        if best_match:
            print(f"[SESSION_SEARCH] Final match: turn {best_match.get('turn_id')} with similarity {best_match.get('similarity'):.3f}")
        else:
            print(f"[SESSION_SEARCH] No match found (threshold={threshold})")
        
        return best_match
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts using embeddings"""
        try:
            # Get embeddings
            emb1 = self._get_embedding(text1)
            emb2 = self._get_embedding(text2)
            
            # Cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            print(f"[SESSION] Similarity calculation error: {e}")
            return 0.0
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding from Ollama"""
        result = requests.post(
            EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text}
        )
        result.raise_for_status()
        return np.array(result.json()["embedding"], dtype=np.float32)
    
    def validate_turn(self, turn_id: int):
        """Mark turn as validated"""
        if 0 <= turn_id < len(self.conversation):
            self.conversation[turn_id]["validated"] = True
            print(f"[SESSION] Turn {turn_id} marked as validated")
    
    def invalidate_turn(self, turn_id: int):
        """Mark turn as invalid (hallucinated or incorrect)"""
        if 0 <= turn_id < len(self.conversation):
            self.conversation[turn_id]["validated"] = False
            print(f"[SESSION] Turn {turn_id} marked as invalid")
    
    def get_turn(self, turn_id: int) -> Optional[Dict]:
        """Get specific turn by ID"""
        if 0 <= turn_id < len(self.conversation):
            return self.conversation[turn_id]
        return None
    
    def get_context_chain(self, turn_id: int) -> List[Dict]:
        """Get full context chain for a turn (including referenced turns)"""
        chain = []
        current_id = turn_id
        
        while current_id is not None and 0 <= current_id < len(self.conversation):
            turn = self.conversation[current_id]
            chain.insert(0, turn)  # Add to beginning
            current_id = turn.get("context_from_turn")
        
        return chain
    
    def save(self):
        """Save session memory to JSON file"""
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "conversation": self.conversation
        }
        
        self.file_path.parent.mkdir(exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[SESSION] Saved {len(self.conversation)} turns to {self.file_path}")
    
    @classmethod
    def load(cls, session_id: str) -> 'SessionMemoryManager':
        """Load session memory from JSON file"""
        manager = cls(session_id)
        
        if manager.file_path.exists():
            with open(manager.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                manager.created_at = data.get("created_at", manager.created_at)
                manager.conversation = data.get("conversation", [])
            
            print(f"[SESSION] Loaded {len(manager.conversation)} turns from {manager.file_path}")
        
        return manager
    
    def __len__(self):
        """Return number of turns in session"""
        return len(self.conversation)
    
    def __repr__(self):
        """String representation"""
        return f"SessionMemoryManager(session_id={self.session_id}, turns={len(self.conversation)})"
