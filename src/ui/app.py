"""
Streamlit UI for the Financial Document Analysis Agent.
Provides interactive interface with citations and execution visibility.
"""

import streamlit as st
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.agents.financial_agent import FinancialAgent
from src.tracing.telemetry import get_telemetry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Financial Document Analysis Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .citation-box {
        background-color: #f0f2f6;
        border-left: 4px solid #4CAF50;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .tool-call-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #fff3e0;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ffb74d;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'agent' not in st.session_state:
        st.session_state.agent = FinancialAgent()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'show_details' not in st.session_state:
        st.session_state.show_details = True
    
    if 'selected_query' not in st.session_state:
        st.session_state.selected_query = None


def display_message(role: str, content: str, citations=None, tool_calls=None):
    """Display a chat message with optional citations and tool calls."""
    with st.chat_message(role):
        # Clean content before display
        if content:
            content = content.strip()
        st.write(content)  # Use st.write instead of st.markdown for better rendering
        
        if citations and st.session_state.show_details:
            with st.expander("📚 View Citations", expanded=False):
                for citation in citations:
                    st.markdown(f"""
                    <div class="citation-box">
                        <strong>[{citation['id']}] {citation['document']}</strong> - Page {citation['page']}<br>
                        <em>Section: {citation['section']}</em><br>
                        <small>Relevance Score: {citation['score']}</small><br>
                        <p style="margin-top:5px;">{citation['content']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        if tool_calls and st.session_state.show_details:
            with st.expander("🔧 Tool Executions", expanded=False):
                for tool_call in tool_calls:
                    st.markdown(f"""
                    <div class="tool-call-box">
                        <strong>Tool:</strong> {tool_call['tool']}<br>
                        <strong>Time:</strong> {tool_call['timestamp']}<br>
                        <strong>Inputs:</strong> {json.dumps(tool_call['inputs'], indent=2)}<br>
                    </div>
                    """, unsafe_allow_html=True)


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.title("📊 Financial Document Analysis Agent")
    st.markdown("Ask questions about your financial documents, analyze charts, and compute metrics.")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Display toggle
        st.session_state.show_details = st.checkbox(
            "Show Citations & Tool Calls",
            value=st.session_state.show_details
        )
        
        # Reset conversation
        if st.button("🔄 Reset Conversation"):
            st.session_state.agent.reset_conversation()
            st.session_state.chat_history = []
            st.success("Conversation reset!")
            st.rerun()
        
        st.divider()
        
        # Statistics
        st.header("📈 Session Stats")
        trace = st.session_state.agent.get_execution_trace()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", len(st.session_state.chat_history))
            st.metric("Retrievals", len(trace.get("retrievals", [])))
        with col2:
            st.metric("Tool Calls", len(trace.get("tool_calls", [])))
        
        st.divider()
        
        # Image upload
        st.header("🖼️ Upload Image")
        uploaded_file = st.file_uploader(
            "Upload financial chart or document image",
            type=["png", "jpg", "jpeg"],
            help="Upload charts, graphs, or scanned documents for analysis"
        )
        
        if uploaded_file:
            # Save uploaded file
            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            image_path = upload_dir / uploaded_file.name
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.image(str(image_path), caption=uploaded_file.name, use_container_width=True)
            st.session_state.uploaded_image = str(image_path)
        else:
            st.session_state.uploaded_image = None
        
        st.divider()
        
        # Example queries with buttons
        st.header("💡 Example Queries")
        st.markdown("Click a question to try it:")
        
        example_queries = [
            "What was Apple's revenue for Q4 2025?",
            "Calculate profit margin for Apple 2025",
            "What were Apple's main revenue segments in 2025?",
            "Compare iPhone revenue between 2024 and 2025",
            "What was Apple's net income for 2025?",
            "Show Apple's operating expenses for 2025"
        ]
        
        for query in example_queries:
            if st.button(query, key=f"btn_{hash(query)}", use_container_width=True):
                st.session_state.selected_query = query
                st.rerun()
    
    # Main chat interface
    st.divider()
    
    # Display chat history
    for message in st.session_state.chat_history:
        display_message(
            message["role"],
            message["content"],
            message.get("citations"),
            message.get("tool_calls")
        )
    
    # Chat input
    prompt = st.chat_input("Ask about financial documents...")
    
    # Check if a query was selected from the example buttons (overrides typed input)
    if st.session_state.selected_query:
        prompt = st.session_state.selected_query
        st.session_state.selected_query = None  # Clear it
    
    if prompt:
        # Display user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })
        display_message("user", prompt)
        
        # Process query
        with st.spinner("Analyzing..."):
            try:
                # Get response from agent
                image_path = st.session_state.get("uploaded_image")
                result = st.session_state.agent.process_query(prompt, image_path)
                
                if result.get("success"):
                    # Display assistant response
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["response"],
                        "citations": result.get("citations", []),
                        "tool_calls": result.get("tool_calls", [])
                    })
                    
                    display_message(
                        "assistant",
                        result["response"],
                        result.get("citations"),
                        result.get("tool_calls")
                    )
                else:
                    error_msg = f"Error: {result.get('error', 'Unknown error occurred')}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
            
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                error_msg = f"An error occurred: {str(e)}"
                st.error(error_msg)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error_msg
                })
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: gray; font-size: 0.9em;">
        Built with Azure OpenAI Agent Framework | OpenTelemetry Tracing Enabled
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
