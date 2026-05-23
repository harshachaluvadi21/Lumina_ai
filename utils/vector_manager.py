import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config

class VectorManager:
    def __init__(self):
        # Setup client (Chroma Cloud or Local Persistent)
        if config.is_chroma_cloud_configured():
            print(f"Connecting to Chroma Cloud (Tenant: {config.CHROMA_TENANT}, DB: {config.CHROMA_DATABASE})...")
            self.chroma_client = chromadb.CloudClient(
                tenant=config.CHROMA_TENANT,
                database=config.CHROMA_DATABASE,
                api_key=config.CHROMA_API_KEY
            )
        else:
            # Setup persistent client
            self.chroma_client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
        
        # Use ChromaDB's default embedding function (downloads and runs MiniLM locally - 100% free and fast)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Initialize or get the single collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="multimodal_content_summarizer",
            embedding_function=self.embedding_function
        )
        
        # Text splitter setup
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    def add_document_to_vector_store(self, user_id: str, document_id: str, text_content: str, title: str) -> int:
        """Splits text content into semantic chunks and indexes them in ChromaDB with metadata."""
        if not text_content.strip():
            return 0
            
        # Split text into chunks
        chunks = self.text_splitter.split_text(text_content)
        
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "user_id": user_id,
                "document_id": document_id,
                "title": title,
                "chunk_index": i
            })
            
        # Bulk insert into ChromaDB
        if ids:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
        return len(ids)

    def similarity_search(self, user_id: str, document_ids: list, query: str, k: int = 5) -> list[dict]:
        """Queries the vector store for top K matching chunks from selected documents."""
        if not document_ids:
            return []
            
        # Filter metadata by user_id and selected document_ids
        where_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$in": document_ids}}
            ]
        }
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where=where_filter
            )
            
            formatted_results = []
            if results and 'documents' in results and results['documents']:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                distances = results['distances'][0] if 'distances' in results else [0.0] * len(docs)
                
                for doc, meta, dist in zip(docs, metas, distances):
                    formatted_results.append({
                        "content": doc,
                        "metadata": meta,
                        "distance": dist
                    })
                    
            return formatted_results
        except Exception as e:
            print(f"Similarity search error: {e}")
            return []

    def delete_document_vectors(self, user_id: str, document_id: str) -> bool:
        """Removes all document vector chunks from the ChromaDB store."""
        try:
            self.collection.delete(
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"document_id": {"$eq": document_id}}
                    ]
                }
            )
            return True
        except Exception as e:
            print(f"Failed to delete vectors for document {document_id}: {e}")
            return False

    def get_document_full_text(self, document_id: str) -> str:
        """Reconstructs the original document text by sorting and joining all indexed chunks from ChromaDB."""
        try:
            results = self.collection.get(
                where={"document_id": {"$eq": document_id}}
            )
            if results and 'documents' in results and results['documents']:
                # Map documents and chunk indices, then sort by index
                chunks_with_indices = []
                for doc, meta in zip(results['documents'], results['metadatas']):
                    idx = meta.get('chunk_index', 0)
                    chunks_with_indices.append((idx, doc))
                
                # Sort based on chunk index
                chunks_with_indices.sort(key=lambda x: x[0])
                
                # Combine
                return "\n\n".join([chunk[1] for chunk in chunks_with_indices])
            return ""
        except Exception as e:
            print(f"Error reconstructing document text: {e}")
            return ""

# Global instance
vector_store = VectorManager()
