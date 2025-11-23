"""
Test script to query FAISS index and show top 5 matching chunks
for the question: "Find the cost of a 3888 sqft Camelia apartment in local documents"
"""

import faiss
import numpy as np
import json
import requests
from pathlib import Path
import sys

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration (matching mcp_server_2.py)
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
ROOT = Path(__file__).parent / "mcp_servers"
FAISS_INDEX_PATH = ROOT / "faiss_index" / "index.bin"
METADATA_PATH = ROOT / "faiss_index" / "metadata.json"

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Ollama"""
    result = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": text})
    result.raise_for_status()
    return np.array(result.json()["embedding"], dtype=np.float32)

def search_faiss(query: str, top_k: int = 5):
    """Search FAISS index and return top K results"""
    
    print(f"[QUERY] {query}\n")
    print("=" * 80)
    
    # Load FAISS index
    if not FAISS_INDEX_PATH.exists():
        print(f"[ERROR] FAISS index not found at {FAISS_INDEX_PATH}")
        return
    
    if not METADATA_PATH.exists():
        print(f"[ERROR] Metadata not found at {METADATA_PATH}")
        return
    
    print(f"[OK] Loading FAISS index from {FAISS_INDEX_PATH}")
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    
    print(f"[OK] Loading metadata from {METADATA_PATH}")
    metadata = json.loads(METADATA_PATH.read_text(encoding='utf-8'))
    
    print(f"[INFO] Index contains {index.ntotal} vectors")
    print(f"[INFO] Metadata contains {len(metadata)} entries\n")
    
    # Get query embedding
    print("[INFO] Getting query embedding from Ollama...")
    query_vec = get_embedding(query).reshape(1, -1)
    print(f"[OK] Query embedding shape: {query_vec.shape}\n")
    
    # Search
    print(f"[SEARCH] Searching for top {top_k} matches...\n")
    distances, indices = index.search(query_vec, k=top_k)
    
    print("=" * 80)
    print(f"TOP {top_k} MATCHING CHUNKS")
    print("=" * 80)
    
    for rank, (idx, distance) in enumerate(zip(indices[0], distances[0]), 1):
        data = metadata[idx]
        
        print(f"\n{'-' * 80}")
        print(f"RANK #{rank}")
        print(f"{'-' * 80}")
        print(f"Distance (L2): {distance:.4f}")
        print(f"Source Document: {data['doc']}")
        print(f"Chunk ID: {data['chunk_id']}")
        print(f"\nCONTENT:")
        print(f"{'-' * 80}")
        # Handle Unicode characters safely
        try:
            print(data['chunk'])
        except UnicodeEncodeError:
            print(data['chunk'].encode('ascii', errors='replace').decode('ascii'))
        print(f"{'-' * 80}")
    
    print("\n" + "=" * 80)
    print("SEARCH COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    query = "Find the cost of a 3888 sqft Camelia apartment in local documents"
    search_faiss(query, top_k=5)
