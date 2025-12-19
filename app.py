"""
Streamlit Chat Interface for Hybrid Financial Chatbot
Beautiful, interactive web UI with conversation memory.
"""

import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.hybrid_chatbot import HybridFinancialChatbot
from datetime import datetime


# Page configuration
st.set_page_config(
    page_title="Financial AI Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling with dark mode support
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #888;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        color: inherit;
    }
    
    /* Light mode styles */
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        color: #000;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4caf50;
        color: #000;
    }
    
    /* Dark mode styles */
    @media (prefers-color-scheme: dark) {
        .user-message {
            background-color: #1e3a5f;
            border-left: 4px solid #2196f3;
            color: #e0e0e0;
        }
        .assistant-message {
            background-color: #1e3a2f;
            border-left: 4px solid #4caf50;
            color: #e0e0e0;
        }
        .sub-header {
            color: #aaa;
        }
    }
    
    /* Force dark mode if Streamlit theme is dark */
    [data-testid="stAppViewContainer"][data-theme="dark"] .user-message {
        background-color: #1e3a5f !important;
        color: #e0e0e0 !important;
    }
    [data-testid="stAppViewContainer"][data-theme="dark"] .assistant-message {
        background-color: #1e3a2f !important;
        color: #e0e0e0 !important;
    }
    
    .source-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .sql-badge {
        background-color: #2196f3;
        color: white;
    }
    .rag-badge {
        background-color: #4caf50;
        color: white;
    }
    .hybrid-badge {
        background-color: #ff9800;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_chatbot():
    """Initialize chatbot (cached to avoid reloading)."""
    return HybridFinancialChatbot(use_llm=True, verbose=True)


def format_source_badge(source):
    """Format source badge HTML."""
    if source == 'sql':
        return '<span class="source-badge sql-badge">🗄️ SQL</span>'
    elif source == 'rag':
        return '<span class="source-badge rag-badge">📚 RAG</span>'
    else:
        return '<span class="source-badge hybrid-badge">🔀 HYBRID</span>'


def display_message(role, content, metadata=None):
    """Display a chat message with styling."""
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 You:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    else:
        source_badge = ""
        if metadata and 'source' in metadata:
            source_badge = format_source_badge(metadata['source'])
        
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Assistant:</strong> {source_badge}<br>
            {content}
        </div>
        """, unsafe_allow_html=True)
        
        # Show additional metadata in expander
        if metadata:
            with st.expander("📊 View Details", expanded=True):
                # Always show SQL query if present
                if 'sql_query' in metadata and metadata['sql_query']:
                    st.write("**🔍 SQL Query:**")
                    st.code(metadata['sql_query'], language='sql')
                
                # Show raw results for debugging
                if 'raw_results' in metadata:
                    if not metadata['raw_results'].empty:
                        st.write("**📋 Query Results:**")
                        st.dataframe(metadata['raw_results'])
                    else:
                        st.error("❌ Query returned 0 rows (empty DataFrame)")
                        st.write("**Debug Info:**")
                        st.json({
                            "row_count": metadata.get('row_count', 0),
                            "success": metadata.get('success', False),
                            "columns": list(metadata['raw_results'].columns) if hasattr(metadata['raw_results'], 'columns') else []
                        })
                elif 'row_count' in metadata:
                    if metadata['row_count'] == 0:
                        st.error(f"❌ Row count: {metadata['row_count']} - No data found!")
                    else:
                        st.warning(f"⚠️ Row count: {metadata['row_count']}")
                
                if 'routing' in metadata:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Confidence", f"{metadata['routing']['confidence']:.0%}")
                    with col2:
                        st.metric("Route", metadata['source'].upper())
                    
                    st.write(f"**💡 Reasoning:**")
                    st.write(metadata['routing']['reasoning'])
                
                if 'chunk_count' in metadata:
                    st.info(f"📄 Retrieved {metadata['chunk_count']} document chunks")


def main():
    """Main Streamlit app."""
    
    # Header
    st.markdown('<div class="main-header">💼 Financial AI Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Intelligent chatbot combining structured data (SQL) and unstructured documents (RAG)</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Model info
        st.info("🤖 **Model:** gemini-2.5-flash-lite")
        
        # Data sources
        st.subheader("📊 Data Sources")
        st.write("**Structured (SQL):**")
        st.write("• 7 companies")
        st.write("• Financial metrics (2023)")
        st.write("")
        st.write("**Unstructured (RAG):**")
        st.write("• 5 documents")
        st.write("• 10-K filings & earnings calls")
        
        # Example queries
        st.subheader("💡 Example Queries")
        
        example_queries = {
            "SQL Queries": [
                "What is Apple's revenue?",
                "Compare Tesla and NVIDIA market cap",
                "Which company has highest P/E ratio?"
            ],
            "RAG Queries": [
                "What are Microsoft's AI initiatives?",
                "Explain Apple's business strategy",
                "What challenges is Meta facing?"
            ]
        }
        
        for category, queries in example_queries.items():
            with st.expander(category):
                for query in queries:
                    if st.button(query, key=query):
                        st.session_state.example_query = query
        
        # Clear chat button
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🔄 Reset Bot", use_container_width=True):
                st.cache_resource.clear()
                if 'chatbot' in st.session_state:
                    del st.session_state.chatbot
                st.session_state.messages = []
                st.rerun()
        
        # Stats
        if 'messages' in st.session_state:
            msg_count = len([m for m in st.session_state.messages if m['role'] == 'user'])
            st.metric("Questions Asked", msg_count)
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'chatbot' not in st.session_state:
        with st.spinner("🔄 Initializing chatbot..."):
            st.session_state.chatbot = initialize_chatbot()
        st.success("✅ Chatbot ready!")
    
    # Display chat history
    for message in st.session_state.messages:
        display_message(
            message['role'],
            message['content'],
            message.get('metadata')
        )
    
    # Handle example query from sidebar
    if 'example_query' in st.session_state:
        user_input = st.session_state.example_query
        del st.session_state.example_query
    else:
        user_input = None
    
    # Chat input
    if prompt := (user_input or st.chat_input("Ask me anything about financial data...")):
        # Add user message
        st.session_state.messages.append({
            'role': 'user',
            'content': prompt,
            'timestamp': datetime.now()
        })
        
        # Display user message
        display_message('user', prompt)
        
        # Get response
        with st.spinner("🤔 Thinking..."):
            try:
                result = st.session_state.chatbot.answer(prompt)
                
                # Prepare metadata
                metadata = {
                    'source': result['source'],
                    'success': result['success'],
                    'routing': result['routing']
                }
                
                if 'sql_query' in result:
                    metadata['sql_query'] = result['sql_query']
                
                if 'chunk_count' in result:
                    metadata['chunk_count'] = result['chunk_count']
                
                # Add assistant message
                st.session_state.messages.append({
                    'role': 'assistant',
                    'content': result['answer'],
                    'metadata': metadata,
                    'timestamp': datetime.now()
                })
                
                # Display assistant message
                display_message('assistant', result['answer'], metadata)
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.session_state.messages.append({
                    'role': 'assistant',
                    'content': error_msg,
                    'timestamp': datetime.now()
                })
                st.error(error_msg)
        
        # Rerun to update chat
        st.rerun()
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🗄️ SQL: Structured financial data")
    with col2:
        st.caption("📚 RAG: Unstructured documents")
    with col3:
        st.caption("🔀 Hybrid: Combined approach")


if __name__ == "__main__":
    main()
