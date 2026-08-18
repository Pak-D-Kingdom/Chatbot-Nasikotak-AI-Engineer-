import os
import copy
import json
import yaml
import glob
import numpy as np
import faiss
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv


load_dotenv()

@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any]

class RAGService:
    def __init__(self, index_dir: str = "faiss_index", model_name: str = "intfloat/multilingual-e5-small"):
        """
        Inisialisasi RAG Service menggunakan multilingual-e5-small dan FAISS.
        """
        self.index_dir = index_dir
        self.model_name = model_name
        self.encoder = SentenceTransformer(model_name)
        self.dimension = self.encoder.get_sentence_embedding_dimension()
        
        
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents: List[Document] = []
        
        os.makedirs(self.index_dir, exist_ok=True)
    def _parse_markdown_file(self, filepath: str) -> Document:
        """
        Membaca file markdown dan memisahkan YAML frontmatter (metadata) dengan content.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata = {}
        page_content = content

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    metadata = {}
                page_content = parts[2].strip()
        
    
        metadata['source'] = os.path.basename(filepath)
        
        return Document(page_content=page_content, metadata=metadata)

    def load_knowledge_base(self, kb_dir: str = "knowledge_base") -> List[Document]:
        """
        Load semua file .md dari folder knowledge_base.
        """
        docs = []
        # Support recursive search in Python 3.5+
        search_pattern = os.path.join(kb_dir, '**', '*.md')
        for filepath in glob.glob(search_pattern, recursive=True):
            doc = self._parse_markdown_file(filepath)
            docs.append(doc)
        return docs

    def chunk_documents(self, documents: List[Document], chunk_size: int = 700, overlap: int = 50) -> List[Document]:
        """
        Chunking dokumen dengan menggabungkan paragraf/section selama 
        ukurannya belum melebihi chunk_size, dan mendukung overlap.
        """
        chunked_docs = []
        for doc in documents:
            text = doc.page_content.strip()
            
            # Jika dokumen pendek, jadikan 1 chunk saja
            if len(text) <= chunk_size:
                doc.metadata['chunk_id'] = 0
                chunked_docs.append(doc)
                continue
                
            # Pisahkan teks berdasarkan paragraf (\n\n)
            paragraphs = text.split('\n\n')
            
            current_chunk = ""
            chunk_idx = 0
            
            for i, p in enumerate(paragraphs):
                p = p.strip()
                if not p:
                    continue
                    
                # Jika ditambah paragraf ini masih cukup
                if len(current_chunk) + len(p) + 2 <= chunk_size:
                    if current_chunk:
                        current_chunk += "\n\n" + p
                    else:
                        current_chunk = p
                else:
                    # Simpan chunk yang sudah penuh
                    if current_chunk:
                        chunk_meta = doc.metadata.copy()
                        chunk_meta['chunk_id'] = chunk_idx
                        chunked_docs.append(Document(page_content=current_chunk, metadata=chunk_meta))
                        chunk_idx += 1
                        
                    # Mulai chunk baru. Untuk overlap, kita ambil sejumlah teks dari akhir current_chunk
                    if current_chunk and overlap > 0:
                        # Ambil `overlap` karakter terakhir, cari batas spasi agar kata tidak terpotong
                        overlap_text = current_chunk[-overlap:]
                        first_space = overlap_text.find(' ')
                        if first_space != -1 and first_space < len(overlap_text) - 1:
                            overlap_text = overlap_text[first_space+1:]
                        current_chunk = overlap_text + "\n\n" + p if overlap_text else p
                    else:
                        current_chunk = p
                        
            # Sisa chunk terakhir
            if current_chunk:
                chunk_meta = doc.metadata.copy()
                chunk_meta['chunk_id'] = chunk_idx
                chunked_docs.append(Document(page_content=current_chunk, metadata=chunk_meta))
                
        return chunked_docs

    def build_index(self, documents: List[Document]):
        """
        Membuat FAISS index dari list documents.
        """
        self.documents = documents
        if not documents:
            print("Warning: Tidak ada dokumen untuk di-index.")
            return

        print(f"Menghasilkan embedding untuk {len(documents)} chunks...")
        
        # Untuk model e5, teks yang akan di-index harus diawali dengan 'passage: '
        texts_to_embed = [f"passage: {doc.page_content}" for doc in documents]
        
        # Generate embeddings
        embeddings = self.encoder.encode(texts_to_embed, normalize_embeddings=True)
        
        # Tambahkan ke FAISS index
        self.index.add(np.array(embeddings, dtype=np.float32))
        print(f"Berhasil membuat index FAISS dengan {self.index.ntotal} vektor.")

    def save_index(self):
        """
        Menyimpan index FAISS dan metadata ke disk.
        """
        index_path = os.path.join(self.index_dir, "index.faiss")
        faiss.write_index(self.index, index_path)
        
        metadata_path = os.path.join(self.index_dir, "metadata.json")
        docs_dict = [{"page_content": d.page_content, "metadata": d.metadata} for d in self.documents]
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(docs_dict, f, ensure_ascii=False, indent=2)
            
        print(f"Index berhasil disimpan di {self.index_dir}/")

    def load_index(self):
        """
        Memuat index FAISS dan metadata dari disk.
        """
        index_path = os.path.join(self.index_dir, "index.faiss")
        metadata_path = os.path.join(self.index_dir, "metadata.json")
        
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError("FAISS index atau metadata tidak ditemukan.")
            
        self.index = faiss.read_index(index_path)
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            docs_dict = json.load(f)
            
        self.documents = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in docs_dict]
        print(f"Berhasil memuat index FAISS dengan {self.index.ntotal} vektor.")

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Helper untuk mengecek apakah metadata dokumen memenuhi kriteria filter.
        """
        for key, value in filters.items():
            if key not in metadata:
                return False
                
            # Jika value berupa list, cek apakah ada irisan (intersection)
            if isinstance(value, list) and isinstance(metadata[key], list):
                if not set(value).intersection(set(metadata[key])):
                    return False
            # Jika value berupa list tapi metadata string/scalar
            elif isinstance(value, list):
                if metadata[key] not in value:
                    return False
            # Jika metadata berupa list tapi value string/scalar (contoh: event_types)
            elif isinstance(metadata[key], list):
                if value not in metadata[key]:
                    return False
            # Exact match biasa
            elif metadata[key] != value:
                return False
                
        return True

    def search(self, query: str, top_k: int = 5, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Mencari top-K dokumen yang paling relevan dengan query.
        """
        if self.index.ntotal == 0:
            return []
            
        # Untuk model e5, query harus diawali dengan 'query: '
        query_text = f"query: {query}"
        
        # Generate embedding
        query_embedding = self.encoder.encode([query_text], normalize_embeddings=True)
        
        # Karena metadata filtering dilakukan secara post-filtering,
        # kita harus mengambil candidate lebih banyak dari FAISS.
        search_k = top_k * 20 if metadata_filters else top_k
        search_k = min(search_k, self.index.ntotal)
        
        distances, indices = self.index.search(np.array(query_embedding, dtype=np.float32), search_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # -1 means not found
                doc = self.documents[idx]
                
                # Apply metadata filtering
                if metadata_filters and not self._matches_filters(doc.metadata, metadata_filters):
                    continue
                    
                # Simpan similarity score
                score = float(distances[0][i])
                
                # Copy doc agar tidak mengubah objek asli di memory/documents list
                
                result_doc = copy.deepcopy(doc)
                result_doc.metadata['relevance_score'] = round(score, 4)
                
                results.append(result_doc)
                
                if len(results) == top_k:
                    break
                    
        # Pastikan terurut berdasarkan relevance_score secara descending
        results.sort(key=lambda x: x.metadata.get('relevance_score', 0.0), reverse=True)
        
        return results

    def construct_context(self, retrieved_docs: List[Document], max_chars: int = 1500) -> str:
        """
        Membangun string context dari dokumen yang terambil untuk prompt LLM.
        """
        context_parts = []
        total_chars = 0
        for i, doc in enumerate(retrieved_docs, 1):
            if doc.metadata.get('relevance_score', 0) < 0.3:
                continue
                
            source = doc.metadata.get('source', 'Unknown source')
            content = doc.page_content
            entry = f"[{source}]\n{content}\n"
            
            if total_chars + len(entry) > max_chars:
                break
                
            context_parts.append(entry)
            total_chars += len(entry)
            
        return "\n".join(context_parts)
