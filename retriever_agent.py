from agent_state import Blackboard
from mcp_servers.multiMCP import MultiMCP
import faiss
import numpy as np
import json
import requests
from pathlib import Path
from typing import Optional, Dict
from utils.memory_validator import is_memory_valid

# Configuration
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
ROOT = Path(__file__).parent / "mcp_servers"
DOCUMENTS_INDEX_PATH = ROOT / "faiss_index" / "documents"
MEMORY_INDEX_PATH = ROOT / "faiss_index" / "memory"

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Ollama"""
    result = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": text})
    result.raise_for_status()
    return np.array(result.json()["embedding"], dtype=np.float32)

class RetrieverAgent:
    def __init__(self, blackboard: Blackboard, multi_mcp: MultiMCP):
        self.blackboard = blackboard
        self.multi_mcp = multi_mcp
        self.session_memory = None  # Will be set by coordinator
    
    def set_session_memory(self, session_memory):
        """Set session memory manager"""
        self.session_memory = session_memory
    
    def search_session_memory(self, query: str) -> Optional[Dict]:
        """
        Search current session for similar Q&A.
        Returns best matching turn if found and validated.
        """
        if not self.session_memory:
            return None
        
        match = self.session_memory.search_similar(query, threshold=0.85)
        
        if match:
            print(f"[SESSION] Found similar turn:")
            print(f"  - Turn ID: {match['turn_id']}")
            print(f"  - Similarity: {match['similarity']:.3f}")
            print(f"  - Confidence: {match['confidence']}")
            print(f"  - Source: {match['source']}")
        
        return match

    async def search_memory_faiss(self, query: str, top_k: int = 3) -> dict:
        """
        Search memory FAISS index for cached answers.
        Returns best match if valid, None otherwise.
        """
        try:
            index_file = MEMORY_INDEX_PATH / "index.bin"
            metadata_file = MEMORY_INDEX_PATH / "metadata.json"
            
            if not index_file.exists() or not metadata_file.exists():
                return None
            
            # Load index and metadata
            index = faiss.read_index(str(index_file))
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            
            if index.ntotal == 0:
                return None
            
            # Get query embedding
            query_vec = get_embedding(query).reshape(1, -1)
            
            # Search
            distances, indices = index.search(query_vec, k=min(top_k, index.ntotal))
            
            # Check best match
            for idx, distance in zip(indices[0], distances[0]):
                if idx >= len(metadata):
                    continue
                    
                memory_entry = metadata[idx]
                
                # Validate memory entry
                if is_memory_valid(memory_entry, query):
                    age_hours = self._get_age_hours(memory_entry.get("timestamp", ""))
                    return {
                        "answer": memory_entry.get("answer", ""),
                        "confidence": memory_entry.get("confidence", 0.0),
                        "source": memory_entry.get("source", ""),
                        "age_hours": age_hours,
                        "distance": float(distance)
                    }
            
            return None
            
        except Exception as e:
            print(f"[MEMORY_SEARCH] Error: {e}")
            return None
    
    def _get_age_hours(self, timestamp_str: str) -> float:
        """Calculate age in hours"""
        from datetime import datetime, timezone
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - timestamp).total_seconds() / 3600
        except:
            return 0.0

    async def search_document_faiss(self, query: str, top_k: int = 5) -> list:
        """
        Search document FAISS index for relevant chunks.
        Returns list of document chunks.
        """
        try:
            index_file = DOCUMENTS_INDEX_PATH / "index.bin"
            metadata_file = DOCUMENTS_INDEX_PATH / "metadata.json"
            
            if not index_file.exists() or not metadata_file.exists():
                return []
            
            # Load index and metadata
            index = faiss.read_index(str(index_file))
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            
            if index.ntotal == 0:
                return []
            
            # Get query embedding
            query_vec = get_embedding(query).reshape(1, -1)
            
            # Search
            distances, indices = index.search(query_vec, k=min(top_k, index.ntotal))
            
            # Extract chunks
            results = []
            for idx in indices[0]:
                if idx < len(metadata):
                    data = metadata[idx]
                    results.append(f"{data['chunk']}\n[Source: {data['doc']}, ID: {data['chunk_id']}]")
            
            return results
            
        except Exception as e:
            print(f"[DOCUMENT_SEARCH] Error: {e}")
            return []

    async def run(self, query: str):
        """
        Fetch context with priority: Session → Conversation FAISS → Documents → Web
        """
        print(f"[RETRIEVER] Gathering context for '{query}'...")
        
        context_results = []
        source_type = None
        
        # 1. Search Session Memory FIRST (current conversation)
        print("[RETRIEVER] Searching session memory...")
        session_match = self.search_session_memory(query)
        
        if session_match:
            context_results.append(f"Session Memory (Turn {session_match['turn_id']}):\n{session_match['answer']}")
            source_type = "session"
            print(f"[SESSION] Using answer from turn {session_match['turn_id']}")
            
            # Store in blackboard and return early
            self.blackboard.state.context_data["initial_retrieval"] = "\n".join(context_results)
            self.blackboard.state.context_data["source"] = source_type
            print(f"[RETRIEVER] Found 1 context source (session)")
            return
        
        # 2. Search Conversation Memory FAISS (with validation)
        print("[RETRIEVER] Searching conversation memory FAISS...")
        memory_match = await self.search_memory_faiss(query)
        
        if memory_match:
            context_results.append(f"Memory (Cached):\n{memory_match['answer']}")
            source_type = "memory"
            print(f"[MEMORY] Using cached answer:")
            print(f"  - Confidence: {memory_match['confidence']}")
            print(f"  - Age: {memory_match['age_hours']:.1f}h")
            print(f"  - Source: {memory_match['source']}")
            print(f"  - Distance: {memory_match['distance']:.4f}")
            
            # Store in blackboard and return early
            self.blackboard.state.context_data["initial_retrieval"] = "\n".join(context_results)
            self.blackboard.state.context_data["source"] = source_type
            print(f"[RETRIEVER] Found 1 context source (memory)")
            return
        
        # 3. Search Document FAISS
        print("[RETRIEVER] Searching document FAISS...")
        doc_results = await self.search_document_faiss(query, top_k=5)
        
        if doc_results:
            doc_text = "\n\n".join(doc_results)
            context_results.append(f"Local Documents:\n{doc_text}")
            source_type = "documents"
            print(f"[DOCUMENTS] Retrieved {len(doc_results)} chunks")
        
        # 4. Store results
        self.blackboard.state.context_data["initial_retrieval"] = "\n".join(context_results)
        self.blackboard.state.context_data["source"] = source_type or "none"
        print(f"[RETRIEVER] Found {len(context_results)} context sources")
