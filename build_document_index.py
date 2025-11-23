"""
Build FAISS index from documents in mcp_servers/documents folder
Supports: PDF, TXT, DOCX files
"""

import faiss
import numpy as np
import json
import requests
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configuration
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 500  # Characters per chunk
OVERLAP = 50  # Overlap between chunks

DOCUMENTS_DIR = Path(__file__).parent / "mcp_servers" / "documents"
INDEX_DIR = Path(__file__).parent / "mcp_servers" / "faiss_index" / "documents"

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Ollama"""
    try:
        result = requests.post(
            EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30
        )
        result.raise_for_status()
        return np.array(result.json()["embedding"], dtype=np.float32)
    except Exception as e:
        print(f"[ERROR] Failed to get embedding: {e}")
        raise

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk)
        
        start += (chunk_size - overlap)
    
    return chunks

def read_txt_file(file_path: Path) -> str:
    """Read text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read {file_path}: {e}")
        return ""

def read_pdf_file(file_path: Path) -> str:
    """Read PDF file using PyPDF2"""
    try:
        import PyPDF2
        text = []
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text.append(page.extract_text())
        return "\n".join(text)
    except ImportError:
        print(f"[WARNING] PyPDF2 not installed, skipping {file_path}")
        return ""
    except Exception as e:
        print(f"[ERROR] Failed to read PDF {file_path}: {e}")
        return ""

def read_docx_file(file_path: Path) -> str:
    """Read DOCX file using python-docx"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        return "\n".join(text)
    except ImportError:
        print(f"[WARNING] python-docx not installed, skipping {file_path}")
        return ""
    except Exception as e:
        print(f"[ERROR] Failed to read DOCX {file_path}: {e}")
        return ""

def read_document(file_path: Path) -> str:
    """Read document based on file extension"""
    ext = file_path.suffix.lower()
    
    if ext == '.txt':
        return read_txt_file(file_path)
    elif ext == '.pdf':
        return read_pdf_file(file_path)
    elif ext == '.docx':
        return read_docx_file(file_path)
    else:
        print(f"[WARNING] Unsupported file type: {ext}")
        return ""

def build_document_index():
    """Build FAISS index from all documents"""
    
    print("=" * 80)
    print("BUILDING DOCUMENT FAISS INDEX")
    print("=" * 80)
    
    # Check if documents directory exists
    if not DOCUMENTS_DIR.exists():
        print(f"[ERROR] Documents directory not found: {DOCUMENTS_DIR}")
        print(f"[INFO] Creating directory...")
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Please add documents to {DOCUMENTS_DIR}")
        return
    
    # Find all supported documents
    supported_extensions = ['.txt', '.pdf', '.docx']
    documents = []
    for ext in supported_extensions:
        documents.extend(DOCUMENTS_DIR.glob(f'*{ext}'))
    
    if not documents:
        print(f"[WARNING] No documents found in {DOCUMENTS_DIR}")
        print(f"[INFO] Supported formats: {', '.join(supported_extensions)}")
        return
    
    print(f"\n[INFO] Found {len(documents)} documents:")
    for doc in documents:
        print(f"  - {doc.name}")
    
    # Process documents
    all_chunks = []
    all_metadata = []
    chunk_id = 0
    
    for doc_path in documents:
        print(f"\n[PROCESSING] {doc_path.name}...")
        
        # Read document
        text = read_document(doc_path)
        if not text:
            print(f"  [SKIP] No text extracted")
            continue
        
        print(f"  [INFO] Extracted {len(text)} characters")
        
        # Chunk text
        chunks = chunk_text(text)
        print(f"  [INFO] Created {len(chunks)} chunks")
        
        # Create embeddings and metadata
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                "chunk_id": chunk_id,
                "chunk": chunk,
                "doc": doc_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
            chunk_id += 1
    
    if not all_chunks:
        print("\n[ERROR] No chunks to index!")
        return
    
    print(f"\n[INFO] Total chunks to index: {len(all_chunks)}")
    print(f"[INFO] Getting embeddings from Ollama...")
    
    # Get embeddings
    embeddings = []
    for i, chunk in enumerate(all_chunks):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(all_chunks)}")
        
        embedding = get_embedding(chunk)
        embeddings.append(embedding)
    
    print(f"  Progress: {len(all_chunks)}/{len(all_chunks)} ✓")
    
    # Create FAISS index
    print(f"\n[INFO] Creating FAISS index...")
    embeddings_array = np.array(embeddings, dtype=np.float32)
    dimension = embeddings_array.shape[1]
    
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    print(f"  [OK] Index created with {index.ntotal} vectors (dimension: {dimension})")
    
    # Save index and metadata
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    index_file = INDEX_DIR / "index.bin"
    metadata_file = INDEX_DIR / "metadata.json"
    
    faiss.write_index(index, str(index_file))
    print(f"  [OK] Saved index to {index_file}")
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Saved metadata to {metadata_file}")
    
    print("\n" + "=" * 80)
    print("INDEX BUILD COMPLETE")
    print("=" * 80)
    print(f"Total documents: {len(documents)}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Index location: {INDEX_DIR}")

if __name__ == "__main__":
    try:
        build_document_index()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Index build interrupted")
    except Exception as e:
        print(f"\n[ERROR] Index build failed: {e}")
        import traceback
        traceback.print_exc()
