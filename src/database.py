"""
Database Layer with DuckDB and Text-to-SQL
Handles structured financial data queries using natural language.
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class FinancialDatabase:
    """Manages DuckDB database and SQL query generation for financial data."""
    
    def __init__(self, csv_path: str = "data/financial_data.csv", verbose: bool = False):
        """Initialize DuckDB and load financial data."""
        self.verbose = verbose
        self.csv_path = Path(csv_path)
        
        # Create in-memory DuckDB connection
        self.conn = duckdb.connect(database=':memory:')
        
        # Load CSV data
        self._load_data()
        
        # Store schema information for SQL generation
        self._extract_schema()
    
    def _load_data(self):
        """Load CSV data into DuckDB."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        
        # Read CSV and create table
        df = pd.read_csv(self.csv_path)
        self.conn.register('financial_data', df)
        
        if self.verbose:
            print(f"Loaded {len(df)} companies into DuckDB")
    
    def _extract_schema(self):
        """Extract schema information for SQL generation."""
        schema_query = "DESCRIBE financial_data"
        schema_df = self.conn.execute(schema_query).fetchdf()
        
        self.columns = schema_df['column_name'].tolist()
        self.column_types = dict(zip(schema_df['column_name'], schema_df['column_type']))
        
        # Store sample values for better SQL generation
        self.sample_data = self.conn.execute("SELECT * FROM financial_data LIMIT 3").fetchdf()
        
        if self.verbose:
            print(f"Schema: {self.columns}")
    
    def get_schema_info(self) -> Dict:
        """Get database schema information."""
        return {
            'table_name': 'financial_data',
            'columns': self.columns,
            'column_types': self.column_types,
            'sample_data': self.sample_data.to_dict('records')
        }
    
    def execute_sql(self, sql_query: str) -> Tuple[pd.DataFrame, bool]:
        """
        Execute SQL query and return results.
        
        Returns:
            Tuple of (results_df, success)
        """
        try:
            result = self.conn.execute(sql_query).fetchdf()
            return result, True
        except Exception as e:
            if self.verbose:
                print(f"SQL Error: {str(e)}")
            return pd.DataFrame(), False
    
    def natural_language_to_sql(self, question: str, llm_function=None) -> str:
        """
        Convert natural language question to SQL query.
        
        Args:
            question: Natural language question
            llm_function: Optional LLM function for SQL generation
        
        Returns:
            SQL query string
        """
        if llm_function:
            # Use LLM for SQL generation
            return self._llm_based_sql_generation(question, llm_function)
        else:
            # Use rule-based SQL generation (fallback)
            return self._rule_based_sql_generation(question)
    
    def _rule_based_sql_generation(self, question: str) -> str:
        """
        Rule-based SQL generation for common query patterns.
        This is a fallback when LLM is not available.
        """
        question_lower = question.lower()
        
        # Pattern 1: "What is [company]'s [metric]?"
        if 'what is' in question_lower or 'what are' in question_lower:
            # Extract company
            company = self._extract_company(question)
            
            # Extract metric
            if 'revenue' in question_lower:
                if company:
                    return f"SELECT company_name, revenue_2023_billions FROM financial_data WHERE company_name ILIKE '%{company}%'"
                return "SELECT company_name, revenue_2023_billions FROM financial_data ORDER BY revenue_2023_billions DESC"
            
            elif 'market cap' in question_lower:
                if company:
                    return f"SELECT company_name, market_cap_billions FROM financial_data WHERE company_name ILIKE '%{company}%'"
                return "SELECT company_name, market_cap_billions FROM financial_data ORDER BY market_cap_billions DESC"
            
            elif 'p/e ratio' in question_lower or 'pe ratio' in question_lower:
                if company:
                    return f"SELECT company_name, pe_ratio FROM financial_data WHERE company_name ILIKE '%{company}%'"
                return "SELECT company_name, pe_ratio FROM financial_data ORDER BY pe_ratio"
            
            elif 'net income' in question_lower:
                if company:
                    return f"SELECT company_name, net_income_2023_billions FROM financial_data WHERE company_name ILIKE '%{company}%'"
                return "SELECT company_name, net_income_2023_billions FROM financial_data ORDER BY net_income_2023_billions DESC"
        
        # Pattern 2: "Compare [companies]"
        if 'compare' in question_lower:
            companies = self._extract_multiple_companies(question)
            if len(companies) >= 2:
                company_filter = " OR ".join([f"company_name ILIKE '%{c}%'" for c in companies])
                return f"SELECT company_name, revenue_2023_billions, net_income_2023_billions, market_cap_billions FROM financial_data WHERE {company_filter}"
        
        # Pattern 3: "Which company has the highest/lowest [metric]?"
        if 'highest' in question_lower or 'largest' in question_lower or 'biggest' in question_lower:
            if 'revenue' in question_lower:
                return "SELECT company_name, revenue_2023_billions FROM financial_data ORDER BY revenue_2023_billions DESC LIMIT 1"
            elif 'market cap' in question_lower:
                return "SELECT company_name, market_cap_billions FROM financial_data ORDER BY market_cap_billions DESC LIMIT 1"
            elif 'net income' in question_lower:
                return "SELECT company_name, net_income_2023_billions FROM financial_data ORDER BY net_income_2023_billions DESC LIMIT 1"
        
        if 'lowest' in question_lower or 'smallest' in question_lower:
            if 'revenue' in question_lower:
                return "SELECT company_name, revenue_2023_billions FROM financial_data ORDER BY revenue_2023_billions ASC LIMIT 1"
            elif 'p/e ratio' in question_lower or 'pe ratio' in question_lower:
                return "SELECT company_name, pe_ratio FROM financial_data ORDER BY pe_ratio ASC LIMIT 1"
        
        # Pattern 4: "List all [sector] companies"
        if 'technology' in question_lower or 'tech' in question_lower:
            return "SELECT company_name, ticker, revenue_2023_billions FROM financial_data WHERE sector = 'Technology'"
        
        if 'consumer' in question_lower:
            return "SELECT company_name, ticker, revenue_2023_billions FROM financial_data WHERE sector = 'Consumer Cyclical'"
        
        # Default: return all data
        return "SELECT * FROM financial_data"
    
    def _extract_company(self, question: str) -> Optional[str]:
        """Extract company name from question."""
        companies = {
            'apple': 'Apple',
            'microsoft': 'Microsoft',
            'alphabet': 'Alphabet',
            'google': 'Alphabet',
            'amazon': 'Amazon',
            'nvidia': 'NVIDIA',
            'tesla': 'Tesla',
            'meta': 'Meta',
            'facebook': 'Meta'
        }
        
        question_lower = question.lower()
        for key, value in companies.items():
            if key in question_lower:
                return value
        
        return None
    
    def _extract_multiple_companies(self, question: str) -> List[str]:
        """Extract multiple company names from question."""
        companies = []
        company_map = {
            'apple': 'Apple',
            'microsoft': 'Microsoft',
            'alphabet': 'Alphabet',
            'google': 'Alphabet',
            'amazon': 'Amazon',
            'nvidia': 'NVIDIA',
            'tesla': 'Tesla',
            'meta': 'Meta',
            'facebook': 'Meta'
        }
        
        question_lower = question.lower()
        for key, value in company_map.items():
            if key in question_lower and value not in companies:
                companies.append(value)
        
        return companies
    
    def _llm_based_sql_generation(self, question: str, llm_function) -> str:
        """
        Use LLM to generate SQL query from natural language.
        
        Args:
            question: Natural language question
            llm_function: Function that takes prompt and returns SQL
        """
        schema_info = self.get_schema_info()
        
        prompt = f"""You are a SQL expert. Convert the following question into a SQL query for DuckDB.

Database Schema:
Table: financial_data
Columns: {', '.join([f"{col} ({self.column_types[col]})" for col in self.columns])}

Sample Data:
{self.sample_data.to_string()}

Question: {question}

IMPORTANT RULES:
1. Generate ONLY the SQL query, no explanations
2. Use proper DuckDB syntax
3. The query should be safe and read-only (SELECT statements only)
4. For company name matching, ALWAYS use ILIKE with wildcards for partial matching
   Example: WHERE company_name ILIKE '%Tesla%' OR company_name ILIKE '%NVIDIA%'
5. Company names in the database may have suffixes like "Inc.", "Corp", "Platforms", etc.
6. NEVER use exact match with IN clause for company names

SQL Query:"""
        
        sql_query = llm_function(prompt)
        
        # Clean up the response
        sql_query = sql_query.strip()
        
        # Remove markdown code blocks if present
        if '```sql' in sql_query:
            sql_query = sql_query.split('```sql')[1].split('```')[0].strip()
        elif '```' in sql_query:
            sql_query = sql_query.split('```')[1].split('```')[0].strip()
        
        # Remove any trailing semicolons
        sql_query = sql_query.rstrip(';')
        
        return sql_query
    
    def query(self, question: str, llm_function=None) -> Dict:
        """
        Query the database using natural language.
        
        Args:
            question: Natural language question
            llm_function: Optional LLM function for SQL generation
        
        Returns:
            Dict with sql_query, results, success, and error (if any)
        """
        # Generate SQL
        sql_query = self.natural_language_to_sql(question, llm_function)
        
        if self.verbose:
            print(f"Generated SQL: {sql_query}")
        
        # Execute SQL
        results_df, success = self.execute_sql(sql_query)
        
        response = {
            'sql_query': sql_query,
            'results': results_df,
            'success': success,
            'row_count': len(results_df) if success else 0
        }
        
        if not success:
            response['error'] = 'SQL execution failed'
        
        return response
    
    def format_results(self, results_df: pd.DataFrame, max_rows: int = 10) -> str:
        """Format query results as a readable string."""
        if results_df.empty:
            return "No results found."
        
        # Limit rows
        display_df = results_df.head(max_rows)
        
        # Format as string
        result_str = display_df.to_string(index=False)
        
        if len(results_df) > max_rows:
            result_str += f"\n\n... and {len(results_df) - max_rows} more rows"
        
        return result_str
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def test_database():
    """Test the database functionality."""
    print("=" * 70)
    print("TESTING DUCKDB TEXT-TO-SQL")
    print("=" * 70)
    
    # Initialize database
    db = FinancialDatabase(verbose=True)
    
    # Test queries
    test_questions = [
        "What is Apple's revenue?",
        "What is the market cap of Tesla?",
        "Compare Apple and Microsoft revenue",
        "Which company has the highest revenue?",
        "What is Microsoft's P/E ratio?",
        "List all technology companies"
    ]
    
    print("\n" + "=" * 70)
    print("RUNNING TEST QUERIES")
    print("=" * 70)
    
    for question in test_questions:
        print(f"\n📊 Question: {question}")
        
        result = db.query(question)
        
        print(f"   SQL: {result['sql_query']}")
        print(f"   Success: {result['success']}")
        
        if result['success'] and not result['results'].empty:
            print(f"   Results:\n{db.format_results(result['results'], max_rows=3)}")
        else:
            print("   No results")
    
    print("\n" + "=" * 70)
    print("✓ Database testing complete")
    print("=" * 70)
    
    db.close()


if __name__ == "__main__":
    test_database()
