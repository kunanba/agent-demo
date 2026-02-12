"""
Main financial agent using Azure OpenAI Agent Framework.
Orchestrates retrieval, tools, and conversation state.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from openai import AzureOpenAI
from azure.ai.inference.models import ChatRequestMessage, UserMessage, AssistantMessage, SystemMessage

from src.tools.retrieval_tool import RetrievalTool
from src.tools.calculator_tool import CalculatorTool
from src.tools.vision_tool import VisionTool
from src.tracing.telemetry import get_telemetry, trace_function

logger = logging.getLogger(__name__)


class ConversationState:
    """Manages conversation history and context."""
    
    def __init__(self, max_history: int = 10):
        self.messages: List[Dict[str, str]] = []
        self.max_history = max_history
        self.retrieved_documents: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if too long (keep first system message + recent messages)
        if len(self.messages) > self.max_history:
            system_msgs = [m for m in self.messages if m["role"] == "system"]
            recent_msgs = [m for m in self.messages if m["role"] != "system"][-self.max_history:]
            self.messages = system_msgs + recent_msgs
    
    def add_retrieval(self, query: str, results: List[Dict[str, Any]]):
        """Track retrieval operations."""
        self.retrieved_documents.append({
            "query": query,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_tool_call(self, tool_name: str, inputs: Dict[str, Any], output: Dict[str, Any]):
        """Track tool usage."""
        self.tool_calls.append({
            "tool": tool_name,
            "inputs": inputs,
            "output": output,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get formatted chat history for the LLM."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]
    
    def clear(self):
        """Clear conversation state."""
        self.messages = []
        self.retrieved_documents = []
        self.tool_calls = []


class FinancialAgent:
    """
    Main agent for financial document analysis.
    
    Capabilities:
    - Search and retrieve information from financial documents
    - Calculate financial metrics and ratios
    - Analyze charts and images
    - Multi-turn conversations with context
    - Full traceability via OpenTelemetry
    """
    
    def __init__(self):
        self.telemetry = get_telemetry()
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        # Initialize tools
        self.retrieval_tool = RetrievalTool()
        self.calculator_tool = CalculatorTool()
        self.vision_tool = VisionTool()
        
        # Conversation state
        self.state = ConversationState()
        
        # System prompt
        self.system_prompt = self._build_system_prompt()
        self.state.add_message("system", self.system_prompt)
        
        logger.info("Financial Agent initialized")
    
    def _build_system_prompt(self) -> str:
        """Build the agent's system prompt."""
        return """You are an expert financial analyst AI assistant. Your role is to help users analyze financial documents, calculate metrics, and extract insights from reports and data.

You have access to the following tools:

1. search_financial_documents: Search through financial documents (earnings reports, statements, filings) to find specific information. Use this when you need to find data from documents.

2. calculate_financial_metric: Calculate financial ratios and metrics like profit margin, ROE, growth rates, etc. Use this when you need to compute metrics from extracted data.

3. analyze_financial_image: Analyze charts, graphs, tables, or scanned documents using vision AI. Use this when the user provides images or asks about visual content.

Guidelines:
- Always cite your sources with document names and page numbers
- Show your work when performing calculations
- Be precise with numerical data
- If you're not certain about information, say so
- Use tools systematically: search first, then calculate or analyze
- Provide context and interpretation with metrics

When answering:
1. Determine if you need to use tools
2. Use retrieval to find relevant information
3. Use calculator for metric computations
4. Use vision for image analysis
5. Synthesize information and provide a clear answer with citations
"""
    
    @trace_function("agent_process_query")
    def process_query(
        self,
        user_query: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the agent workflow.
        
        Args:
            user_query: The user's question or request
            image_path: Optional path to an image to analyze
            
        Returns:
            Dictionary with response, citations, and execution trace
        """
        with self.telemetry.trace_operation("process_query", {"query": user_query[:100]}):
            # Add user message to state
            self.state.add_message("user", user_query)
            
            # Determine workflow
            workflow = self._plan_workflow(user_query, image_path)
            
            # Execute workflow
            response_data = self._execute_workflow(workflow, user_query, image_path)
            
            # Generate final response
            final_response = self._generate_response(user_query, response_data)
            
            # Add assistant message to state
            self.state.add_message("assistant", final_response["response"])
            
            return final_response
    
    def _plan_workflow(self, query: str, image_path: Optional[str]) -> List[str]:
        """
        Determine which tools to use based on the query.
        
        Returns list of tool names in order of execution.
        """
        workflow = []
        
        query_lower = query.lower()
        
        # Check if image analysis is needed
        if image_path or any(word in query_lower for word in ["chart", "image", "graph", "picture", "visual"]):
            workflow.append("vision")
        
        # Check if calculation is needed (check this BEFORE retrieval for better prioritization)
        calculation_keywords = [
            "calculate", "compute", "margin", "ratio", "growth", "percentage",
            "profit margin", "gross margin", "operating margin", "roe", "roa",
            "current ratio", "debt to equity", "p/e", "eps", "growth rate"
        ]
        if any(word in query_lower for word in calculation_keywords):
            # For calculations, we often need to retrieve data first, then calculate
            workflow.append("retrieval")
            workflow.append("calculator")
        # Check if retrieval is needed (but not already added)
        elif any(word in query_lower for word in ["what", "find", "show", "document", "report", "where", "when", "summarize"]):
            workflow.append("retrieval")
        
        # Default to retrieval if no specific tool identified
        if not workflow:
            workflow.append("retrieval")
        
        logger.info(f"Planned workflow: {workflow}")
        return workflow
    
    @trace_function("execute_workflow")
    def _execute_workflow(
        self,
        workflow: List[str],
        query: str,
        image_path: Optional[str]
    ) -> Dict[str, Any]:
        """Execute the planned workflow and gather information."""
        results = {
            "retrieval": None,
            "calculations": [],
            "vision": None
        }
        
        # Execute vision analysis
        if "vision" in workflow and image_path:
            vision_result = self.vision_tool(image_path=image_path, query=query)
            results["vision"] = vision_result
            self.state.add_tool_call("analyze_financial_image", {"image_path": image_path}, vision_result)
        
        # Execute retrieval
        if "retrieval" in workflow:
            retrieval_result = self.retrieval_tool(query)
            results["retrieval"] = retrieval_result
            self.state.add_retrieval(query, retrieval_result.get("citations", []))
            self.state.add_tool_call("search_financial_documents", {"query": query}, retrieval_result)
        
        # Execute calculations if needed
        if "calculator" in workflow:
            # Let the LLM extract numbers and determine the calculation
            # We'll prompt it to use the calculator in the response generation
            results["use_calculator"] = True
        
        return results
    
    @trace_function("generate_response")
    def _generate_response(self, query: str, workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final response using LLM with workflow results."""
        
        # Build context from workflow results
        context_parts = []
        
        if workflow_results.get("retrieval"):
            context_parts.append("Retrieved Information:")
            context_parts.append(workflow_results["retrieval"]["context"])
        
        if workflow_results.get("vision"):
            context_parts.append("\nImage Analysis:")
            context_parts.append(workflow_results["vision"].get("analysis", ""))
        
        context = "\n\n".join(context_parts) if context_parts else "No additional context available."
        
        # Build messages for LLM
        calculation_guidance = ""
        if workflow_results.get("use_calculator"):
            calculation_guidance = """
IMPORTANT: If you need to calculate financial metrics (like profit margin, ROE, growth rate, etc.):
1. Extract the required numbers from the context
2. State what calculation you're performing
3. Show the formula
4. Provide the result with the calculation breakdown
5. Include your interpretation

For example:
- Profit Margin = (Net Income / Revenue) × 100
- If Net Income = $X and Revenue = $Y, then: ($X / $Y) × 100 = Z%
"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""User Query: {query}

Context from Tools:
{context}

{calculation_guidance}

Please provide a comprehensive answer to the user's query based on the retrieved information. Include:
1. Direct answer to the question
2. Supporting data and citations
3. Any relevant calculations or interpretations (show your work!)
4. Additional insights if applicable

Format citations as [Document Name, Page X].
Use simple, clear formatting without special characters.
"""}
        ]
        
        # Call LLM
        with self.telemetry.trace_operation("llm_call"):
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0.1,  # Low temperature for factual responses
                max_tokens=1000
            )
        
        answer = response.choices[0].message.content
        
        # Clean up any encoding issues
        if answer:
            # Remove any weird unicode characters that might cause rendering issues
            answer = answer.replace('\u200b', '')  # Zero-width space
            answer = answer.replace('\ufeff', '')  # BOM
            answer = answer.strip()
        
        # Collect citations
        citations = []
        if workflow_results.get("retrieval"):
            citations = workflow_results["retrieval"].get("citations", [])
        
        return {
            "response": answer,
            "citations": citations,
            "tool_calls": self.state.tool_calls[-len([w for w in ["retrieval", "vision", "calculator"] if w in workflow_results]):],
            "success": True
        }
    
    def reset_conversation(self):
        """Reset conversation state."""
        self.state.clear()
        self.state.add_message("system", self.system_prompt)
        logger.info("Conversation reset")
    
    def get_execution_trace(self) -> Dict[str, Any]:
        """Get detailed execution trace for observability."""
        return {
            "conversation_history": self.state.messages,
            "retrievals": self.state.retrieved_documents,
            "tool_calls": self.state.tool_calls
        }
