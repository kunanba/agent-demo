# Financial Document Analysis Agent

An agentic AI system that analyzes financial documents (PDFs and images) using Azure OpenAI Agent Framework with observability via OpenTelemetry.

## Problem Statement

Financial analysts and investors spend significant time manually reviewing earnings reports, financial statements, and quarterly filings. This agent automates:
- Extracting key financial metrics from documents
- Answering questions about financial data
- Comparing data across multiple documents
- Analyzing charts and tables in images using vision models

## Features

- **Hybrid Retrieval**: Combines semantic and keyword search with reranking
- **Custom Tools**: 
  - Financial calculator for metrics (P/E ratio, margins, growth rates)
  - Vision tool for extracting data from charts/images
  - Document comparison tool
- **State Management**: Tracks conversation history and multi-step reasoning
- **Observability**: Full OpenTelemetry tracing for all operations
- **Explainability**: Shows sources, citations, and execution steps in UI

## Architecture

### Components

1. **Document Ingestion**: Processes PDFs with structure-aware chunking
2. **Retrieval System**: Azure AI Search with hybrid search and reranking
3. **Agent Orchestration**: Azure OpenAI Agent Framework with custom tools
4. **Observability**: OpenTelemetry with Jaeger/Azure Monitor integration
5. **UI**: Streamlit interface showing citations and agent reasoning

### Tech Stack

- Azure OpenAI (GPT-4 and GPT-4 Vision)
- Azure AI Search (hybrid search)
- Azure Agent Framework
- OpenTelemetry
- Streamlit
- LangChain (for document processing)

## Setup

### Prerequisites

- Python 3.10+
- Azure subscription with:
  - Azure OpenAI service
  - Azure AI Search service
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd agent-demo
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

### Environment Variables

```
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
# Optional: separate vision deployment (GPT-4o/4-turbo are multimodal)
# AZURE_OPENAI_VISION_DEPLOYMENT=gpt-4-vision
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX=financial-docs

# OpenTelemetry (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
JAEGER_ENABLED=true
```

## Usage

### 1. Add Sample Documents

Add your sample financial documents:
- Place PDFs in `data/sample_pdfs/`
- Place chart images in `data/images/`

You can use:
- Public company earnings reports (Apple, Microsoft, Tesla investor relations)
- Sample financial statements
- Mock documents for testing

### 2. Ingest Documents

```bash
python -m src.ingestion.document_processor --input ./data/sample_pdfs
```

This will extract, chunk, embed, and index your documents.

### 3. Run the Agent UI

```bash
streamlit run src/ui/app.py
```

Open http://localhost:8501 in your browser.

### 4. Create Golden Test Set (Optional)

After adding documents, create a proper evaluation set:

```bash
python generate_golden_set.py
```

This interactive script helps you:
- Test queries against your actual documents
- Record expected answers
- Build a custom golden set

### 5. Run Evaluation

```bash
python -m evaluation.eval_script
```

## Project Structure

```
agent-demo/
├── src/
│   ├── agents/
│   │   └── financial_agent.py      # Main agent orchestration
│   ├── tools/
│   │   ├── retrieval_tool.py       # Hybrid search retrieval
│   │   ├── calculator_tool.py      # Financial calculations
│   │   ├── vision_tool.py          # Image/chart analysis
│   │   └── comparison_tool.py      # Document comparison
│   ├── ingestion/
│   │   └── document_processor.py   # PDF processing & indexing
│   ├── retrieval/
│   │   ├── chunking.py             # Structure-aware chunking
│   │   └── reranker.py             # Result reranking
│   ├── tracing/
│   │   └── telemetry.py            # OpenTelemetry setup
│   └── ui/
│       └── app.py                  # Streamlit interface
├── data/
│   ├── sample_pdfs/                # Sample financial documents
│   └── images/                     # Sample charts/tables
├── evaluation/
│   ├── golden_set.json             # Test questions
│   └── eval_script.py              # Evaluation runner
├── docs/
│   ├── architecture.md             # Architecture overview
│   └── deployment.md               # Cloud deployment guide
├── requirements.txt
├── .env.example
└── README.md
```

## Example Queries

- "What was the revenue for Q4 2023?"
- "Calculate the profit margin for the last quarter"
- "Compare revenue growth between 2022 and 2023"
- "What does this chart show?" (with image upload)
- "Extract the P/E ratio from the financial statements"

## Retrieval Improvements

1. **Structure-Aware Chunking**: Preserves table structure, respects section boundaries
2. **Hybrid Search**: Combines semantic (vector) and keyword (BM25) search
3. **Metadata Filtering**: Filters by document type, date range, company
4. **Reranking**: Cross-encoder reranking for improved relevance

## Observability

View traces in Jaeger:
```bash
docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

Open http://localhost:16686 to view trace data.

## Evaluation

The evaluation script tests:
- Answer accuracy against golden set
- Citation quality (grounding)
- Tool usage correctness
- Latency metrics

Results are saved to `evaluation/results.json`

## Cloud Deployment

See [docs/deployment.md](docs/deployment.md) for deployment guides for:
- Azure (Container Apps, OpenAI, AI Search)
- AWS (ECS, Bedrock, OpenSearch)
- GCP (Cloud Run, Vertex AI, Vertex AI Search)

## Design Trade-offs

1. **Chunking Strategy**: Fixed-size with overlap vs structure-aware
   - Chose structure-aware to preserve tables and sections
   - Trade-off: More complex, but better context preservation

2. **Search Approach**: Pure vector vs hybrid
   - Chose hybrid for better handling of specific terms and metrics
   - Trade-off: Slightly higher latency, better relevance

3. **Agent Framework**: Custom vs Azure Agent Framework
   - Chose Azure for native integration and enterprise features
   - Trade-off: Azure-specific, but production-ready

## License

MIT
