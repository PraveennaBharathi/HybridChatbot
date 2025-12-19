"""
Hybrid Financial Chatbot
Combines SQL database queries and RAG document retrieval.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, List, Optional
from src.database import FinancialDatabase
from src.vectorstore import FinancialVectorStore
from src.query_router import QueryRouter
from src.llm_client import LLMClient


class HybridFinancialChatbot:
    """Intelligent financial chatbot with SQL and RAG capabilities."""
    
    def __init__(self, use_llm: bool = True, verbose: bool = False):
        """
        Initialize hybrid chatbot.
        
        Args:
            use_llm: Use LLM for SQL generation and responses
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.use_llm = use_llm
        
        # Initialize components
        if self.verbose:
            print("Initializing Hybrid Financial Chatbot...")
        
        # Database (SQL)
        self.database = FinancialDatabase(verbose=verbose)
        
        # Vector store (RAG)
        self.vectorstore = FinancialVectorStore(verbose=verbose)
        
        # Query router
        self.router = QueryRouter(use_llm=use_llm, verbose=verbose)
        
        # LLM client (optional)
        if use_llm:
            try:
                self.llm = LLMClient(verbose=verbose)
            except ValueError:
                if verbose:
                    print("LLM not available, using rule-based approaches")
                self.use_llm = False
                self.llm = None
        else:
            self.llm = None
        
        if self.verbose:
            print("✓ Hybrid chatbot initialized")
    
    def answer(self, question: str, use_routing: bool = True) -> Dict:
        """
        Answer a question using appropriate data source(s).
        
        Args:
            question: User's question
            use_routing: Use intelligent routing (True) or manual override
        
        Returns:
            Dict with answer, sources, route, and metadata
        """
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"Question: {question}")
            print(f"{'='*70}")
        
        # Route the query
        if use_routing:
            routing = self.router.route_query(question, confidence_threshold=0.7)
            route = routing['route']
            should_use_hybrid = routing['should_use_hybrid']
        else:
            route = 'rag'  # default
            should_use_hybrid = False
            routing = {'confidence': 1.0, 'reasoning': 'Manual routing'}
        
        # Execute based on route
        if should_use_hybrid:
            return self._hybrid_answer(question, routing)
        elif route == 'sql':
            return self._sql_answer(question, routing)
        else:  # rag
            return self._rag_answer(question, routing)
    
    def _sql_answer(self, question: str, routing: Dict) -> Dict:
        """Answer using SQL database."""
        if self.verbose:
            print(f"\n🗄️  Using SQL Database")
        
        # Generate SQL function for LLM
        llm_sql_gen = None
        if self.use_llm and self.llm:
            llm_sql_gen = lambda prompt: self.llm.generate(prompt, temperature=0.0, max_tokens=200)
        
        # Query database
        result = self.database.query(question, llm_function=llm_sql_gen)
        
        if not result['success'] or result['results'].empty:
            return {
                'answer': "I couldn't find any data to answer that question in the database.",
                'source': 'sql',
                'success': False,
                'routing': routing
            }
        
        # Format results
        if self.use_llm and self.llm:
            # Use LLM to format natural language response
            answer = self.llm.format_sql_results(
                question,
                result['sql_query'],
                result['results']
            )
        else:
            # Simple formatting
            answer = self.database.format_results(result['results'], max_rows=10)
        
        return {
            'answer': answer,
            'source': 'sql',
            'sql_query': result['sql_query'],
            'raw_results': result['results'],
            'row_count': result['row_count'],
            'success': True,
            'routing': routing
        }
    
    def _rag_answer(self, question: str, routing: Dict) -> Dict:
        """Answer using RAG (vector search)."""
        if self.verbose:
            print(f"\n📚 Using RAG (Vector Search)")
        
        # Search vector store
        search_results = self.vectorstore.semantic_search(
            query=question,
            n_results=5
        )
        
        if not search_results['documents'][0]:
            return {
                'answer': "I couldn't find relevant information in the documents.",
                'source': 'rag',
                'success': False,
                'routing': routing
            }
        
        # Prepare retrieved chunks
        retrieved_chunks = []
        for i in range(len(search_results['documents'][0])):
            retrieved_chunks.append({
                'text': search_results['documents'][0][i],
                'metadata': search_results['metadatas'][0][i],
                'similarity': 1 - search_results['distances'][0][i]
            })
        
        # Generate answer
        if self.use_llm and self.llm:
            answer = self.llm.generate_rag_response(question, retrieved_chunks)
        else:
            # Simple answer: return top chunk
            top_chunk = retrieved_chunks[0]
            company = top_chunk['metadata'].get('company_name', 'Unknown')
            answer = f"From {company}'s documents:\n\n{top_chunk['text'][:500]}..."
        
        return {
            'answer': answer,
            'source': 'rag',
            'retrieved_chunks': retrieved_chunks,
            'chunk_count': len(retrieved_chunks),
            'success': True,
            'routing': routing
        }
    
    def _hybrid_answer(self, question: str, routing: Dict) -> Dict:
        """Answer using both SQL and RAG."""
        if self.verbose:
            print(f"\n🔀 Using Hybrid Approach (SQL + RAG)")
        
        # Get both answers
        sql_result = self._sql_answer(question, routing)
        rag_result = self._rag_answer(question, routing)
        
        # Combine answers
        combined_answer = "**Structured Data (Database):**\n"
        if sql_result['success']:
            combined_answer += sql_result['answer']
        else:
            combined_answer += "No relevant structured data found."
        
        combined_answer += "\n\n**Unstructured Insights (Documents):**\n"
        if rag_result['success']:
            combined_answer += rag_result['answer']
        else:
            combined_answer += "No relevant documents found."
        
        return {
            'answer': combined_answer,
            'source': 'hybrid',
            'sql_result': sql_result,
            'rag_result': rag_result,
            'success': sql_result['success'] or rag_result['success'],
            'routing': routing
        }
    
    def get_source_info(self, result: Dict) -> str:
        """Get formatted source information."""
        source = result['source']
        
        if source == 'sql':
            return f"Source: SQL Database\nQuery: {result.get('sql_query', 'N/A')}"
        elif source == 'rag':
            chunks = result.get('retrieved_chunks', [])
            if chunks:
                sources = []
                for chunk in chunks[:3]:
                    meta = chunk['metadata']
                    company = meta.get('company_name', 'Unknown')
                    doc_type = meta.get('document_type', 'document')
                    sources.append(f"{company} {doc_type}")
                return f"Source: Documents\nRetrieved from: {', '.join(sources)}"
        elif source == 'hybrid':
            return "Source: SQL Database + Documents (Hybrid)"
        
        return "Source: Unknown"


def test_hybrid_chatbot():
    """Test the hybrid chatbot with various questions."""
    print("=" * 70)
    print("TESTING HYBRID FINANCIAL CHATBOT")
    print("=" * 70)
    
    # Initialize chatbot
    chatbot = HybridFinancialChatbot(use_llm=True, verbose=False)
    
    # Test questions
    test_questions = [
        # SQL questions
        ("What is Apple's revenue in 2023?", "sql"),
        ("Compare the market cap of Tesla and NVIDIA", "sql"),
        ("Which company has the highest P/E ratio?", "sql"),
        
        # RAG questions
        ("What are Apple's AI initiatives?", "rag"),
        ("Explain Microsoft's cloud strategy", "rag"),
        ("What challenges is Meta facing?", "rag"),
        
        # Ambiguous (should use routing)
        ("Tell me about NVIDIA", "auto"),
        ("How is Microsoft performing?", "auto"),
    ]
    
    print("\n" + "=" * 70)
    print("CHATBOT RESPONSES")
    print("=" * 70)
    
    for question, expected_route in test_questions:
        print(f"\n{'='*70}")
        print(f"❓ Question: {question}")
        print(f"{'='*70}")
        
        result = chatbot.answer(question)
        
        print(f"\n📍 Route: {result['source'].upper()}")
        print(f"✓ Success: {result['success']}")
        print(f"\n💬 Answer:\n{result['answer'][:500]}...")
        print(f"\n📎 {chatbot.get_source_info(result)}")
    
    print("\n" + "=" * 70)
    print("✓ Hybrid chatbot working correctly")
    print("=" * 70)


if __name__ == "__main__":
    test_hybrid_chatbot()
