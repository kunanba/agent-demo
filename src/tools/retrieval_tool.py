"""
Retrieval tool with hybrid search and reranking.
Combines semantic and keyword search for better financial document retrieval.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

from src.tracing.telemetry import get_telemetry, trace_function

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Represents a retrieved document chunk with relevance information."""
    content: str
    document_name: str
    page_number: int
    section: str
    score: float
    chunk_id: str
    metadata: Dict[str, Any]


class HybridRetriever:
    """
    Implements hybrid search combining:
    1. Semantic search (vector similarity)
    2. Keyword search (BM25)
    3. Cross-encoder reranking
    """
    
    def __init__(self):
        self.telemetry = get_telemetry()
        
        # Azure Search configuration
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX", "financial-docs")
        
        # Initialize Azure OpenAI for embeddings
        from openai import AzureOpenAI
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Reranking is handled by Azure AI Search hybrid RRF (Reciprocal Rank Fusion)
        logger.info("Using Azure AI Search hybrid search (keyword + vector with RRF)")
        
        # Search client
        if self.search_endpoint and self.search_key:
            self.credential = AzureKeyCredential(self.search_key)
            self.search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.index_name,
                credential=self.credential
            )
        else:
            logger.warning("Azure Search not configured")
            self.search_client = None
        
        self.top_k = int(os.getenv("TOP_K_RESULTS", "5"))
    
    @trace_function("retrieve_documents")
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_reranking: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve documents using hybrid search.
        
        Args:
            query: Search query
            top_k: Number of results to return (default from config)
            filters: Optional metadata filters (e.g., {'document_name': 'Q4_2023'})
            use_reranking: Whether to apply cross-encoder reranking
            
        Returns:
            List of retrieval results with citations
        """
        if not self.search_client:
            logger.error("Search client not initialized")
            return []
        
        top_k = top_k or self.top_k
        
        with self.telemetry.trace_operation("hybrid_search", {
            "query": query,
            "top_k": top_k,
            "use_reranking": use_reranking
        }) as span:
            # Generate query embedding using Azure OpenAI
            embedding_response = self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-3-large",
                dimensions=1536  # Use 1536 for compatibility
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Build filter expression
            filter_expr = self._build_filter(filters) if filters else None
            
            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k * 2,  # Get more for reranking
                fields="embedding"
            )
            
            try:
                # Perform hybrid search (keyword + vector)
                # Note: Azure semantic reranking requires semantic configuration in index
                results = self.search_client.search(
                    search_text=query,  # Keyword search (BM25)
                    vector_queries=[vector_query],  # Vector search (semantic)
                    filter=filter_expr,
                    top=top_k,
                    select=["id", "content", "document_name", "page_number", "section", "chunk_type"]
                )
                
                # Convert to RetrievalResult objects
                retrieval_results = []
                for result in results:
                    retrieval_results.append(RetrievalResult(
                        content=result.get("content", ""),
                        document_name=result.get("document_name", ""),
                        page_number=result.get("page_number", 0),
                        section=result.get("section", ""),
                        score=result.get("@search.score", 0.0),
                        chunk_id=result.get("id", ""),
                        metadata={
                            "chunk_type": result.get("chunk_type", "text")
                        }
                    ))
                
                span.set_attribute("results_count", len(retrieval_results))
                
                # Hybrid search combines keyword + vector automatically via RRF
                logger.info(f"Retrieved {len(retrieval_results)} documents using hybrid search")
                return retrieval_results
                
            except Exception as e:
                logger.error(f"Search error: {e}")
                span.set_attribute("error", str(e))
                return []
    
    def _build_filter(self, filters: Dict[str, Any]) -> str:
        """Build OData filter expression from filter dict."""
        filter_parts = []
        
        for key, value in filters.items():
            if isinstance(value, str):
                filter_parts.append(f"{key} eq '{value}'")
            elif isinstance(value, (int, float)):
                filter_parts.append(f"{key} eq {value}")
            elif isinstance(value, list):
                # OR condition for multiple values
                or_parts = [f"{key} eq '{v}'" if isinstance(v, str) else f"{key} eq {v}" for v in value]
                filter_parts.append(f"({' or '.join(or_parts)})")
        
        return " and ".join(filter_parts)
    
    @trace_function("rerank_results")
    def _rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank results using cross-encoder for better relevance.
        
        The cross-encoder evaluates query-document pairs directly,
        providing more accurate relevance scores than bi-encoder embeddings.
        """
        if not results:
            return results
        
        # Prepare query-document pairs
        pairs = [[query, result.content] for result in results]
        
        # Get reranking scores
        rerank_scores = self.reranker.predict(pairs)
        
        # Update scores and sort
        for result, score in zip(results, rerank_scores):
            result.score = float(score)
        
        # Sort by reranked score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Reranked {len(results)} results, returning top {top_k}")
        return results[:top_k]
    
    def get_context_string(self, results: List[RetrievalResult]) -> str:
        """
        Format retrieval results as a context string for the agent.
        Includes citations for grounding.
        """
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            citation = f"[{i}] {result.document_name}, Page {result.page_number}, Section: {result.section}"
            content = f"{citation}\n{result.content}\n"
            context_parts.append(content)
        
        return "\n---\n".join(context_parts)
    
    def get_citations(self, results: List[RetrievalResult]) -> List[Dict[str, Any]]:
        """
        Get structured citation information for UI display.
        """
        citations = []
        for i, result in enumerate(results, 1):
            citations.append({
                "id": i,
                "document": result.document_name,
                "page": result.page_number,
                "section": result.section,
                "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "score": round(result.score, 3)
            })
        return citations


class RetrievalTool:
    """Tool wrapper for agent integration."""
    
    def __init__(self):
        self.retriever = HybridRetriever()
    
    @property
    def name(self) -> str:
        return "search_financial_documents"
    
    @property
    def description(self) -> str:
        return """Search financial documents for relevant information.
        
        Use this tool to find specific information from earnings reports, financial statements, 
        and quarterly filings. The tool uses hybrid search (semantic + keyword) with reranking 
        for accurate results.
        
        Input should be a clear, specific question or search query.
        
        Examples:
        - "What was the total revenue for Q4 2023?"
        - "Find information about operating expenses"
        - "What are the key risk factors mentioned?"
        """
    
    def __call__(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the retrieval tool.
        
        Args:
            query: Search query
            **kwargs: Optional parameters (filters, top_k, use_reranking)
            
        Returns:
            Dictionary with context and citations
        """
        results = self.retriever.retrieve(query, **kwargs)
        
        return {
            "context": self.retriever.get_context_string(results),
            "citations": self.retriever.get_citations(results),
            "num_results": len(results)
        }
