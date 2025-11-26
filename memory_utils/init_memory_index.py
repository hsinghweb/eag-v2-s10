"""
Initialize the Conversation Memory (Tier 2) FAISS index.
This creates an empty index that will be populated as the agent learns from successful interactions.
"""

import faiss
import numpy as np
import json
from pathlib import Path

# Configuration
ROOT = Path(__file__).parent / "mcp_servers" / "faiss_index" / "memory"
INDEX_FILE = ROOT / "index.bin"
METADATA_FILE = ROOT / "metadata.json"
EMBEDDING_DIM = 768  # nomic-embed-text dimension

def initialize_memory_index():
    """Create empty FAISS index for conversation memory"""
    
    # Create directory if it doesn't exist
    ROOT.mkdir(parents=True, exist_ok=True)
    
    # Create empty FAISS index (L2 distance)
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    
    # Save empty index
    faiss.write_index(index, str(INDEX_FILE))
    print(f"✅ Created empty FAISS index: {INDEX_FILE}")
    
    # Create empty metadata
    metadata = []
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Created empty metadata: {METADATA_FILE}")
    
    print(f"\n🎉 Memory index initialized successfully!")
    print(f"   - Index vectors: {index.ntotal}")
    print(f"   - Dimension: {EMBEDDING_DIM}")

if __name__ == "__main__":
    initialize_memory_index()
