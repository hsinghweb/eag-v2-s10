"""
Initialize empty memory FAISS index
"""

import faiss
import numpy as np
import json
from pathlib import Path

# Configuration
EMBED_DIM = 768  # nomic-embed-text dimension
MEMORY_INDEX_PATH = Path(__file__).parent.parent / "mcp_servers" / "faiss_index" / "memory"

def initialize_memory_index():
    """Create empty FAISS index for memory"""
    
    print("[INIT] Creating empty memory FAISS index...")
    
    # Create empty FAISS index (L2 distance)
    index = faiss.IndexFlatL2(EMBED_DIM)
    
    # Save empty index
    index_file = MEMORY_INDEX_PATH / "index.bin"
    faiss.write_index(index, str(index_file))
    print(f"[OK] Created empty index at {index_file}")
    
    # Create empty metadata
    metadata = []
    metadata_file = MEMORY_INDEX_PATH / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[OK] Created empty metadata at {metadata_file}")
    
    print(f"[OK] Memory FAISS index initialized successfully")
    print(f"    - Index vectors: {index.ntotal}")
    print(f"    - Metadata entries: {len(metadata)}")

if __name__ == "__main__":
    initialize_memory_index()
