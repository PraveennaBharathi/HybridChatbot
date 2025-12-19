"""
Vector Store Implementation with ChromaDB
Handles embedding generation and vector storage with metadata filtering.

Process Flow:
1. Load preprocessed chunks (our 372 chunks)
2. Generate embeddings using sentence-transformers
3. Store vectors + metadata in ChromaDB
4. Enable semantic search with metadata filtering
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm
import numpy as np


class FinancialVectorStore:
    """Manages vector embeddings and ChromaDB storage for financial documents."""
    
    def __init__(
        self, 
        collection_name: str = "financial_documents",
        persist_directory: str = "data/chromadb",
        embedding_model: str = "all-MiniLM-L6-v2",
        verbose: bool = False
    ):
        """Initialize vector store with embedding model and ChromaDB."""
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        
        # Load embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Financial documents with semantic search"}
            )
    
    def embed_text(self, text: str) -> List[float]:
        """Convert text to embedding vector."""
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embed multiple texts efficiently in batches."""
        embeddings = self.embedding_model.encode(
            texts, 
            batch_size=batch_size,
            show_progress_bar=self.verbose,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def add_documents(self, chunks: List[Dict]):
        """Add preprocessed chunks to vector store."""
        if not chunks:
            return
        
        # Extract texts and metadata
        texts = [chunk['text'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        ids = [f"chunk_{i}_{metadatas[i].get('ticker', 'unknown')}" for i in range(len(chunks))]
        
        # Generate embeddings
        embeddings = self.embed_batch(texts, batch_size=32)
        
        # Clean metadata (ChromaDB expects string values)
        cleaned_metadatas = []
        for meta in metadatas:
            cleaned_meta = {k: str(v) for k, v in meta.items()}
            cleaned_metadatas.append(cleaned_meta)
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=cleaned_metadatas,
            ids=ids
        )
    
    def semantic_search(
        self, 
        query: str, 
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Perform semantic search with optional metadata filtering.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Filter by metadata (e.g., {"ticker": "AAPL"})
        
        Returns:
            Dict with documents, metadatas, distances
        """
        query_embedding = self.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        return results
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store."""
        count = self.collection.count()
        
        # Sample some documents to get metadata distribution
        if count > 0:
            sample = self.collection.get(limit=min(100, count))
            
            # Count by company
            companies = {}
            doc_types = {}
            
            for meta in sample['metadatas']:
                ticker = meta.get('ticker', 'Unknown')
                companies[ticker] = companies.get(ticker, 0) + 1
                
                doc_type = meta.get('document_type', 'Unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            return {
                'total_chunks': count,
                'companies': companies,
                'document_types': doc_types
            }
        
        return {'total_chunks': 0}


def load_and_vectorize_all_documents(
    processed_dir: str = "data/processed",
    collection_name: str = "financial_documents",
    verbose: bool = True
):
    """Load all preprocessed documents and vectorize them."""
    
    # Initialize vector store
    vector_store = FinancialVectorStore(collection_name=collection_name, verbose=verbose)
    
    # Load all processed documents
    processed_path = Path(processed_dir)
    json_files = list(processed_path.glob("*_processed.json"))
    
    if verbose:
        print(f"Loading {len(json_files)} processed document files...")
    
    all_chunks = []
    for json_file in sorted(json_files):
        with open(json_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        all_chunks.extend(chunks)
    
    if verbose:
        print(f"Vectorizing {len(all_chunks)} chunks...")
    
    # Vectorize and store
    vector_store.add_documents(all_chunks)
    
    if verbose:
        stats = vector_store.get_collection_stats()
        print(f"✓ Vectorization complete: {stats['total_chunks']} chunks stored")
    
    return vector_store


if __name__ == "__main__":
    # Run the complete vectorization pipeline
    vector_store = load_and_vectorize_all_documents(verbose=True)
    
    # Demo: Test semantic search
    print("\nTesting semantic search...")
    test_queries = [
        "What are Apple's AI initiatives?",
        "Microsoft cloud revenue growth",
        "NVIDIA data center performance"
    ]
    
    for query in test_queries:
        results = vector_store.semantic_search(query, n_results=1)
        if results['documents'][0]:
            print(f"\nQuery: {query}")
            print(f"Top match: {results['metadatas'][0][0].get('company_name')} (similarity: {1 - results['distances'][0][0]:.3f})")
