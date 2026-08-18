import os
import sys

# Ensure src is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.rag_service import RAGService
from src.config import FAISS_INDEX_DIR, KNOWLEDGE_BASE_DIR

def main():
    print("Inisialisasi RAG Service...")
    rag = RAGService(index_dir=FAISS_INDEX_DIR)
    
    print(f"Memuat dokumen dari {KNOWLEDGE_BASE_DIR}...")
    docs = rag.load_knowledge_base(KNOWLEDGE_BASE_DIR)
    print(f"Berhasil memuat {len(docs)} dokumen.")
    
    print("Melakukan chunking dokumen...")
    chunked_docs = rag.chunk_documents(docs)
    print(f"Berhasil membuat {len(chunked_docs)} chunks.")
    
    print("Membangun ulang FAISS index...")
    rag.build_index(chunked_docs)
    
    print("Menyimpan index ke disk...")
    rag.save_index()
    print("Proses update index selesai!")

if __name__ == "__main__":
    main()
