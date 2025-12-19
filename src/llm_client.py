"""
LLM Client for SQL Generation and RAG Response Generation
Supports Google Gemini API (free tier).
"""

import os
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv


class LLMClient:
    """Client for interacting with LLM APIs."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash-lite", verbose: bool = False):
        """
        Initialize LLM client.
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            model: Model name (default: gemini-2.5-flash-lite)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        # Format model name correctly for the new SDK
        if not model.startswith('models/'):
            self.model_name = f"models/{model}"
        else:
            self.model_name = model
        
        # Load environment variables
        load_dotenv()
        
        # Get API key
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Configure Gemini client
        self.client = genai.Client(api_key=self.api_key)
        
        if self.verbose:
            print(f"Initialized LLM: {model}")
    
    def generate(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            return response.text
        
        except Exception as e:
            if self.verbose:
                print(f"LLM Error: {str(e)}")
            return ""
    
    def generate_sql(self, question: str, schema_info: dict) -> str:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: Natural language question
            schema_info: Database schema information
        
        Returns:
            SQL query string
        """
        columns_desc = ', '.join([
            f"{col} ({schema_info['column_types'][col]})" 
            for col in schema_info['columns']
        ])
        
        prompt = f"""You are a SQL expert. Convert the following question into a SQL query for DuckDB.

Database Schema:
Table: {schema_info['table_name']}
Columns: {columns_desc}

Question: {question}

Rules:
1. Generate ONLY the SQL query, no explanations or markdown
2. Use proper DuckDB syntax
3. Use SELECT statements only (read-only)
4. Use LIKE for text matching with wildcards (e.g., LIKE '%Apple%')
5. Be case-insensitive where appropriate
6. Return relevant columns only

SQL Query:"""
        
        sql_query = self.generate(prompt, temperature=0.0, max_tokens=200)
        
        # Clean up response
        sql_query = sql_query.strip()
        
        # Remove markdown code blocks
        if '```sql' in sql_query:
            sql_query = sql_query.split('```sql')[1].split('```')[0].strip()
        elif '```' in sql_query:
            sql_query = sql_query.split('```')[1].split('```')[0].strip()
        
        # Remove trailing semicolons
        sql_query = sql_query.rstrip(';')
        
        return sql_query
    
    def generate_rag_response(
        self, 
        question: str, 
        retrieved_chunks: list, 
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Generate response using retrieved chunks (RAG).
        
        Args:
            question: User question
            retrieved_chunks: List of retrieved text chunks with metadata
            conversation_history: Optional conversation history
        
        Returns:
            Generated response
        """
        # Format retrieved context
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            company = metadata.get('company_name', 'Unknown')
            doc_type = metadata.get('document_type', 'document')
            
            context_parts.append(f"[Source {i} - {company} {doc_type}]\n{text}\n")
        
        context = "\n".join(context_parts)
        
        # Build prompt
        prompt = f"""You are a financial analyst assistant. Answer the question based on the provided context.

Context from financial documents:
{context}

Question: {question}

Instructions:
1. Answer based ONLY on the provided context
2. Be concise and factual
3. Cite sources when possible (e.g., "According to Apple's earnings transcript...")
4. If the context doesn't contain enough information, say so
5. Use clear, professional language

Answer:"""
        
        response = self.generate(prompt, temperature=0.3, max_tokens=500)
        
        return response
    
    def format_sql_results(self, question: str, sql_query: str, results_df) -> str:
        """
        Format SQL query results into natural language response.
        
        Args:
            question: Original question
            sql_query: Executed SQL query
            results_df: Query results DataFrame
        
        Returns:
            Natural language response
        """
        if results_df.empty:
            return "I couldn't find any data matching your query."
        
        # Convert results to string
        results_str = results_df.to_string(index=False, max_rows=10)
        
        prompt = f"""Convert the following SQL query results into a natural language answer.

Question: {question}

SQL Query: {sql_query}

Results:
{results_str}

Instructions:
1. Provide a clear, concise answer to the question
2. Include specific numbers and company names
3. Format numbers with appropriate units (billions, millions, etc.)
4. Be professional and factual
5. Keep it brief (2-3 sentences max)

Answer:"""
        
        response = self.generate(prompt, temperature=0.2, max_tokens=300)
        
        return response


def test_llm_client():
    """Test LLM client functionality."""
    print("=" * 70)
    print("TESTING LLM CLIENT")
    print("=" * 70)
    
    try:
        # Initialize client
        llm = LLMClient(verbose=True)
        
        # Test basic generation
        print("\n📝 Test 1: Basic Generation")
        response = llm.generate("What is 2+2? Answer in one word.", temperature=0.0)
        print(f"Response: {response}")
        
        # Test SQL generation
        print("\n📝 Test 2: SQL Generation")
        schema_info = {
            'table_name': 'financial_data',
            'columns': ['company_name', 'revenue_2023_billions', 'market_cap_billions'],
            'column_types': {
                'company_name': 'VARCHAR',
                'revenue_2023_billions': 'DOUBLE',
                'market_cap_billions': 'DOUBLE'
            }
        }
        
        sql = llm.generate_sql("What is Apple's revenue?", schema_info)
        print(f"Generated SQL: {sql}")
        
        print("\n✓ LLM client working correctly")
        
    except ValueError as e:
        print(f"\n⚠️  {str(e)}")
        print("\nTo use LLM features:")
        print("1. Get a free API key from: https://makersuite.google.com/app/apikey")
        print("2. Create a .env file with: GOOGLE_API_KEY=your_key_here")
        print("\nThe system will work with rule-based SQL generation as fallback.")
    
    print("=" * 70)


if __name__ == "__main__":
    test_llm_client()
