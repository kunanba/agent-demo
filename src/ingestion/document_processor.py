"""
Document ingestion and processing for financial PDFs.
Implements structure-aware chunking to preserve tables and sections.
"""

import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from pypdf import PdfReader
import pandas as pd
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.core.credentials import AzureKeyCredential
from sentence_transformers import SentenceTransformer

from src.tracing.telemetry import get_telemetry, trace_function

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of document content with metadata."""
    id: str
    content: str
    document_name: str
    page_number: int
    chunk_index: int
    chunk_type: str  # 'text', 'table', 'section_header'
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class StructureAwareChunker:
    """Chunks documents while preserving structure like tables and sections."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.telemetry = get_telemetry()
    
    @trace_function("chunk_document")
    def chunk_text(self, text: str, page_num: int, doc_name: str) -> List[DocumentChunk]:
        """
        Chunk text with structure awareness.
        Detects section headers and preserves context.
        """
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        chunk_index = 0
        current_section = "Introduction"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers (all caps, or numbered sections)
            if self._is_section_header(line):
                # Save current chunk if it exists
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk)
                    chunks.append(DocumentChunk(
                        id=f"{doc_name}_p{page_num}_c{chunk_index}",
                        content=chunk_content,
                        document_name=doc_name,
                        page_number=page_num,
                        chunk_index=chunk_index,
                        chunk_type="text",
                        metadata={"section": current_section}
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0
                
                current_section = line
                current_chunk.append(f"Section: {line}")
                current_size = len(line)
                continue
            
            # Add line to current chunk
            line_size = len(line)
            if current_size + line_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_content = '\n'.join(current_chunk)
                chunks.append(DocumentChunk(
                    id=f"{doc_name}_p{page_num}_c{chunk_index}",
                    content=chunk_content,
                    document_name=doc_name,
                    page_number=page_num,
                    chunk_index=chunk_index,
                    chunk_type="text",
                    metadata={"section": current_section}
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk[-3:]) if len(current_chunk) >= 3 else ''
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text)
            
            current_chunk.append(line)
            current_size += line_size
        
        # Save final chunk
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunks.append(DocumentChunk(
                id=f"{doc_name}_p{page_num}_c{chunk_index}",
                content=chunk_content,
                document_name=doc_name,
                page_number=page_num,
                chunk_index=chunk_index,
                chunk_type="text",
                metadata={"section": current_section}
            ))
        
        return chunks
    
    def _is_section_header(self, line: str) -> bool:
        """Detect if a line is likely a section header."""
        if len(line) < 5 or len(line) > 100:
            return False
        
        # Check for numbered sections (1. Introduction, 1.1 Revenue)
        if line[:3].replace('.', '').replace(' ', '').isdigit():
            return True
        
        # Check for all caps headers
        if line.isupper() and len(line.split()) <= 8:
            return True
        
        # Common financial report sections
        financial_sections = [
            'REVENUE', 'EXPENSES', 'ASSETS', 'LIABILITIES', 'CASH FLOW',
            'INCOME STATEMENT', 'BALANCE SHEET', 'EXECUTIVE SUMMARY',
            'MANAGEMENT DISCUSSION', 'RISK FACTORS', 'QUARTERLY RESULTS'
        ]
        
        return any(section in line.upper() for section in financial_sections)


class DocumentProcessor:
    """Processes and indexes financial documents."""
    
    def __init__(self):
        self.telemetry = get_telemetry()
        self.chunker = StructureAwareChunker(
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200"))
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Azure Search configuration
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX", "financial-docs")
        
        if self.search_endpoint and self.search_key:
            self.credential = AzureKeyCredential(self.search_key)
            self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Create search index if it doesn't exist."""
        with self.telemetry.trace_operation("create_search_index"):
            index_client = SearchIndexClient(
                endpoint=self.search_endpoint,
                credential=self.credential
            )
            
            # Define index schema
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="document_name", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
                SearchableField(name="chunk_type", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="section", type=SearchFieldDataType.String, filterable=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=384,
                    vector_search_profile_name="myHnswProfile"
                ),
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw",
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(name="myHnsw")
                ],
            )
            
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            try:
                index_client.create_or_update_index(index)
                logger.info(f"Search index '{self.index_name}' created/updated")
            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                raise
    
    @trace_function("process_pdf")
    def process_pdf(self, pdf_path: str) -> List[DocumentChunk]:
        """Process a PDF file and extract chunks."""
        doc_name = Path(pdf_path).stem
        chunks = []
        
        try:
            reader = PdfReader(pdf_path)
            logger.info(f"Processing {doc_name} ({len(reader.pages)} pages)")
            
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                
                if text.strip():
                    page_chunks = self.chunker.chunk_text(text, page_num, doc_name)
                    chunks.extend(page_chunks)
                    
                    self.telemetry.add_event("page_processed", {
                        "document": doc_name,
                        "page": page_num,
                        "chunks": len(page_chunks)
                    })
            
            logger.info(f"Extracted {len(chunks)} chunks from {doc_name}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            raise
    
    @trace_function("generate_embeddings")
    def generate_embeddings(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Generate embeddings for chunks."""
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
        
        return chunks
    
    @trace_function("index_chunks")
    def index_chunks(self, chunks: List[DocumentChunk]):
        """Index chunks in Azure AI Search."""
        if not self.search_endpoint or not self.search_key:
            logger.warning("Azure Search not configured, skipping indexing")
            return
        
        search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        
        # Prepare documents for upload
        documents = []
        for chunk in chunks:
            doc = {
                "id": chunk.id,
                "content": chunk.content,
                "document_name": chunk.document_name,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "chunk_type": chunk.chunk_type,
                "section": chunk.metadata.get("section", ""),
                "embedding": chunk.embedding
            }
            documents.append(doc)
        
        # Upload in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                result = search_client.upload_documents(documents=batch)
                logger.info(f"Indexed batch {i // batch_size + 1}: {len(batch)} documents")
            except Exception as e:
                logger.error(f"Error indexing batch: {e}")
                raise
    
    def process_directory(self, directory: str):
        """Process all PDFs in a directory."""
        pdf_dir = Path(directory)
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        all_chunks = []
        for pdf_file in pdf_files:
            chunks = self.process_pdf(str(pdf_file))
            all_chunks.extend(chunks)
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        all_chunks = self.generate_embeddings(all_chunks)
        
        # Index in search
        logger.info("Indexing documents...")
        self.index_chunks(all_chunks)
        
        logger.info(f"Processing complete: {len(all_chunks)} total chunks indexed")


if __name__ == "__main__":
    import sys
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Process financial documents")
    parser.add_argument("--input", required=True, help="Input directory containing PDFs")
    args = parser.parse_args()
    
    from dotenv import load_dotenv
    load_dotenv()
    
    processor = DocumentProcessor()
    processor.process_directory(args.input)
