"""
Auto-initialize all FAISS indices (Tier 1, 2, 3) if they don't exist.
This ensures the system can start cleanly without manual index creation.
"""

import faiss
import numpy as np
import json
from pathlib import Path

# Configuration
EMBEDDING_DIM = 768  # nomic-embed-text dimension
PROJECT_ROOT = Path(__file__).parent.parent
MCP_ROOT = PROJECT_ROOT / "mcp_servers" / "faiss_index"

# Index paths
MEMORY_INDEX_PATH = MCP_ROOT / "memory"  # Tier 2: Conversation Memory
DOCUMENTS_INDEX_PATH = MCP_ROOT / "documents"  # Tier 3: Document Memory

def ensure_index_exists(index_path: Path, index_name: str) -> bool:
    """
    Ensure FAISS index exists at the given path.
    Creates empty index if it doesn't exist.
    
    Returns:
        bool: True if index was created, False if it already existed
    """
    index_file = index_path / "index.bin"
    metadata_file = index_path / "metadata.json"
    
    # Check if both files exist
    if index_file.exists() and metadata_file.exists():
        return False  # Already exists
    
    # Create directory
    index_path.mkdir(parents=True, exist_ok=True)
    
    # Create empty FAISS index (L2 distance)
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    
    # Save empty index
    faiss.write_index(index, str(index_file))
    
    # Create empty metadata
    metadata = []
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✅ Created {index_name}: {index_path}")
    return True

def initialize_all_indices():
    """
    Initialize all FAISS indices if they don't exist.
    
    Tier 1 (Session Memory): Managed in-memory, no FAISS index needed
    Tier 2 (Conversation Memory): FAISS index for cross-session cache
    Tier 3 (Document Memory): FAISS index for local documents
    """
    print("🔍 Checking FAISS indices...")
    
    created_any = False
    
    # Tier 2: Conversation Memory
    if ensure_index_exists(MEMORY_INDEX_PATH, "Conversation Memory (Tier 2)"):
        created_any = True
    
    # Tier 3: Document Memory
    if ensure_index_exists(DOCUMENTS_INDEX_PATH, "Document Memory (Tier 3)"):
        created_any = True
    
    if created_any:
        print("✅ FAISS indices initialized")
    else:
        print("✅ All FAISS indices already exist")

if __name__ == "__main__":
    initialize_all_indices()
