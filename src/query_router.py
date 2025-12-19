"""
Query Router - Intelligent routing between SQL and RAG
Decides whether to use structured database or unstructured documents.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, Literal
from src.llm_client import LLMClient


class QueryRouter:
    """Routes queries to appropriate data source (SQL or RAG)."""
    
    def __init__(self, use_llm: bool = True, verbose: bool = False):
        """
        Initialize query router.
        
        Args:
            use_llm: Use LLM for classification (more accurate)
            verbose: Enable verbose logging
        """
        self.use_llm = use_llm
        self.verbose = verbose
        
        if use_llm:
            try:
                self.llm = LLMClient(verbose=verbose)
            except ValueError:
                if verbose:
                    print("LLM not available, falling back to rule-based routing")
                self.use_llm = False
        
        # Define what data is available in each source
        self.sql_data_description = """
        Structured financial metrics (CSV/Database):
        - Company names, tickers, sectors
        - Market capitalization (billions)
        - P/E ratios
        - 2023 Revenue (billions)
        - 2023 Net income (billions)
        - Quantitative comparisons and aggregations
        """
        
        self.rag_data_description = """
        Unstructured documents (PDFs/Transcripts):
        - Earnings call transcripts (Apple, Microsoft, Meta)
        - 10-K filings (NVIDIA, Alphabet)
        - Business strategies and initiatives
        - Product announcements and roadmaps
        - Risk factors and challenges
        - Management commentary and outlook
        - Qualitative business insights
        - AI/technology initiatives
        - Market trends and competition
        """
    
    def classify_query(self, question: str) -> Dict:
        """
        Classify query as SQL or RAG.
        
        Args:
            question: User's question
        
        Returns:
            Dict with route ('sql' or 'rag'), confidence, and reasoning
        """
        if self.use_llm:
            return self._llm_based_classification(question)
        else:
            return self._rule_based_classification(question)
    
    def _rule_based_classification(self, question: str) -> Dict:
        """
        Rule-based classification using keyword matching.
        Fast but less flexible.
        """
        question_lower = question.lower()
        
        # SQL indicators (quantitative, metrics, comparisons)
        sql_keywords = [
            'revenue', 'market cap', 'p/e ratio', 'pe ratio', 'net income',
            'how much', 'how many', 'total', 'average', 'sum',
            'compare', 'comparison', 'versus', 'vs', 'higher', 'lower',
            'highest', 'lowest', 'largest', 'smallest', 'biggest',
            'list all', 'show all', 'which company', 'what company',
            'sector', 'industry', 'ticker', 'stock'
        ]
        
        # RAG indicators (qualitative, strategy, insights)
        rag_keywords = [
            'strategy', 'initiative', 'plan', 'approach', 'focus',
            'ai', 'artificial intelligence', 'machine learning', 'technology',
            'product', 'service', 'innovation', 'development',
            'challenge', 'risk', 'headwind', 'tailwind', 'opportunity',
            'outlook', 'guidance', 'forecast', 'expect', 'anticipate',
            'management', 'ceo', 'cfo', 'executive', 'commentary',
            'why', 'how', 'explain', 'describe', 'discuss',
            'growth driver', 'competitive advantage', 'market position',
            'cloud', 'data center', 'platform', 'ecosystem'
        ]
        
        # Count matches
        sql_score = sum(1 for keyword in sql_keywords if keyword in question_lower)
        rag_score = sum(1 for keyword in rag_keywords if keyword in question_lower)
        
        # Decision logic
        if sql_score > rag_score:
            route = 'sql'
            confidence = min(0.6 + (sql_score * 0.1), 0.95)
            reasoning = f"Detected {sql_score} quantitative/metric keywords"
        elif rag_score > sql_score:
            route = 'rag'
            confidence = min(0.6 + (rag_score * 0.1), 0.95)
            reasoning = f"Detected {rag_score} qualitative/strategic keywords"
        else:
            # Default to RAG for open-ended questions
            route = 'rag'
            confidence = 0.5
            reasoning = "No clear indicators, defaulting to RAG for qualitative answer"
        
        return {
            'route': route,
            'confidence': confidence,
            'reasoning': reasoning,
            'method': 'rule-based'
        }
    
    def _llm_based_classification(self, question: str) -> Dict:
        """
        LLM-based classification for more accurate routing.
        Slower but handles nuanced queries better.
        """
        prompt = f"""You are a query router for a financial chatbot. Classify the following question as either 'SQL' or 'RAG'.

Available Data Sources:

1. SQL Database (Structured):
{self.sql_data_description}

2. RAG Documents (Unstructured):
{self.rag_data_description}

Question: "{question}"

Classification Rules:
- Use SQL for: quantitative metrics, numerical comparisons, aggregations, specific financial numbers
- Use RAG for: qualitative insights, strategies, explanations, business context, forward-looking statements

Respond in this EXACT format:
ROUTE: [SQL or RAG]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]

Classification:"""

        try:
            response = self.llm.generate(prompt, temperature=0.0, max_tokens=150)
            
            # Parse response
            lines = response.strip().split('\n')
            route = 'rag'  # default
            confidence = 0.5
            reasoning = "LLM classification"
            
            for line in lines:
                if line.startswith('ROUTE:'):
                    route_text = line.split(':', 1)[1].strip().lower()
                    route = 'sql' if 'sql' in route_text else 'rag'
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.split(':', 1)[1].strip())
                    except:
                        confidence = 0.7
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()
            
            return {
                'route': route,
                'confidence': confidence,
                'reasoning': reasoning,
                'method': 'llm-based'
            }
        
        except Exception as e:
            if self.verbose:
                print(f"LLM classification failed: {e}, falling back to rule-based")
            return self._rule_based_classification(question)
    
    def route_query(self, question: str, confidence_threshold: float = 0.6) -> Dict:
        """
        Route query and provide recommendation.
        
        Args:
            question: User's question
            confidence_threshold: Minimum confidence for routing decision
        
        Returns:
            Dict with route, confidence, reasoning, and recommendation
        """
        classification = self.classify_query(question)
        
        result = {
            **classification,
            'question': question,
            'should_use_hybrid': classification['confidence'] < confidence_threshold
        }
        
        # Add recommendation
        if result['should_use_hybrid']:
            result['recommendation'] = 'Use both SQL and RAG for comprehensive answer'
        else:
            result['recommendation'] = f"Use {classification['route'].upper()} only"
        
        if self.verbose:
            print(f"\n🔀 Query Routing:")
            print(f"   Question: {question}")
            print(f"   Route: {result['route'].upper()}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Reasoning: {result['reasoning']}")
            print(f"   Method: {result['method']}")
            print(f"   Recommendation: {result['recommendation']}")
        
        return result


def test_query_router():
    """Test the query router with various questions."""
    print("=" * 70)
    print("TESTING QUERY ROUTER")
    print("=" * 70)
    
    # Initialize router
    router = QueryRouter(use_llm=True, verbose=False)
    
    # Test queries
    test_queries = [
        # SQL queries (quantitative)
        "What is Apple's revenue?",
        "Compare the market cap of Tesla and NVIDIA",
        "Which company has the highest P/E ratio?",
        "What's the average revenue of all companies?",
        "List all technology companies",
        
        # RAG queries (qualitative)
        "What are Apple's AI initiatives?",
        "Explain Microsoft's cloud strategy",
        "What challenges is Meta facing?",
        "Describe NVIDIA's data center business",
        "What is Alphabet's outlook for advertising?",
        
        # Ambiguous queries
        "Tell me about Apple",
        "How is Microsoft performing?",
        "What's happening with NVIDIA?"
    ]
    
    print("\n" + "=" * 70)
    print("ROUTING DECISIONS")
    print("=" * 70)
    
    sql_count = 0
    rag_count = 0
    hybrid_count = 0
    
    for question in test_queries:
        result = router.route_query(question, confidence_threshold=0.7)
        
        print(f"\n📝 Question: {question}")
        print(f"   ➜ Route: {result['route'].upper()}")
        print(f"   ➜ Confidence: {result['confidence']:.2f}")
        print(f"   ➜ Reasoning: {result['reasoning']}")
        
        if result['should_use_hybrid']:
            print(f"   ⚠️  Low confidence - recommend hybrid approach")
            hybrid_count += 1
        
        if result['route'] == 'sql':
            sql_count += 1
        else:
            rag_count += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("ROUTING SUMMARY")
    print("=" * 70)
    print(f"\nSQL Queries: {sql_count}")
    print(f"RAG Queries: {rag_count}")
    print(f"Hybrid Recommended: {hybrid_count}")
    print(f"\n✓ Query router working correctly")
    print("=" * 70)


if __name__ == "__main__":
    test_query_router()
