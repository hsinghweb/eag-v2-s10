"""
Complete Memory System Reset
Clears all memory tiers and reinitializes them for a fresh start.
"""

import shutil
import json
import faiss
import numpy as np
from pathlib import Path

def reset_memory():
    """Reset all three memory tiers"""
    
    print("🧹 Resetting Memory System...\n")
    
    # 1. Clear Session Memory (Tier 1)
    print("1️⃣ Clearing Session Memory (Tier 1)...")
    session_dir = Path("memory")
    if session_dir.exists():
        for file in session_dir.glob("session_*.json"):
            file.unlink()
            print(f"   ✅ Deleted: {file.name}")
    
    # Clear session ID file
    session_id_file = Path(".last_session_id")
    if session_id_file.exists():
        session_id_file.unlink()
        print(f"   ✅ Deleted: .last_session_id")
    
    # 2. Reset Conversation Memory (Tier 2)
    print("\n2️⃣ Resetting Conversation Memory (Tier 2)...")
    memory_index_dir = Path("mcp_servers/faiss_index")
    
    # Delete old index files
    for file in ["index.bin", "metadata.json"]:
        file_path = memory_index_dir / file
        if file_path.exists():
            file_path.unlink()
            print(f"   ✅ Deleted: {file}")
    
    # Create fresh empty index
    EMBEDDING_DIM = 768
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    faiss.write_index(index, str(memory_index_dir / "index.bin"))
    
    with open(memory_index_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump([], f, indent=2)
    
    print(f"   ✅ Created fresh FAISS index (dim={EMBEDDING_DIM})")
    
    # 3. Document Memory (Tier 3) - Keep intact but show status
    print("\n3️⃣ Document Memory (Tier 3)...")
    doc_index = memory_index_dir / "documents" / "index.bin"
    if doc_index.exists():
        index = faiss.read_index(str(doc_index))
        print(f"   ℹ️  Keeping document index ({index.ntotal} vectors)")
    else:
        print(f"   ⚠️  No document index found")
    
    print("\n🎉 Memory system reset complete!")
    print("\nNext steps:")
    print("1. Run: uv run main.py")
    print("2. Test: 'My favorite color is blue.'")
    print("3. Test: 'What is my favorite color?'")

if __name__ == "__main__":
    reset_memory()
