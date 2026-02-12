# Quick Reference Guide

## Project Structure

```
agent-demo/
├── src/                          # Source code
│   ├── agents/
│   │   └── financial_agent.py    # Main agent orchestrator
│   ├── tools/
│   │   ├── retrieval_tool.py     # Hybrid search with reranking
│   │   ├── calculator_tool.py    # Financial calculations
│   │   └── vision_tool.py        # Image/chart analysis
│   ├── ingestion/
│   │   └── document_processor.py # PDF processing & indexing
│   ├── tracing/
│   │   └── telemetry.py          # OpenTelemetry setup
│   └── ui/
│       └── app.py                # Streamlit interface
├── evaluation/
│   ├── golden_set.json           # Test questions
│   └── eval_script.py            # Evaluation runner
├── docs/
│   ├── architecture.md           # System architecture
│   ├── deployment.md             # Cloud deployment guide
│   └── PRESENTATION_GUIDE.md     # Presentation tips
├── data/
│   ├── sample_pdfs/              # Place PDFs here
│   └── images/                   # Place charts/images here
├── requirements.txt              # Dependencies
├── .env.example                  # Environment template
├── quickstart.py                 # Setup helper
└── README.md                     # Main documentation
```

## Setup Steps

### 1. Environment Setup

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure credentials
```

### 2. Azure Resources Needed

**Required**:
- Azure OpenAI Service with GPT-4 deployment
- Azure OpenAI Service with GPT-4 Vision deployment
- Azure AI Search service

**Optional** (for full functionality):
- Jaeger for tracing visualization

### 3. Configuration (.env)

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_VISION_DEPLOYMENT=gpt-4-vision

AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX=financial-docs
```

## Running the System

### Option 1: Streamlit UI (Recommended for Demo)

```powershell
streamlit run src/ui/app.py
```

Features:
- Interactive chat
- Citation display
- Tool execution visibility
- Image upload
- Session statistics

### Option 2: Process Documents

```powershell
# Add PDFs to data/sample_pdfs/
python -m src.ingestion.document_processor --input ./data/sample_pdfs
```

This will:
- Extract text from PDFs
- Create structure-aware chunks
- Generate embeddings
- Index in Azure AI Search

### Option 3: Run Evaluation

```powershell
python -m evaluation.eval_script
```

Results saved to `evaluation/results.json`

### Option 4: Direct Agent Usage (Python)

```python
from dotenv import load_dotenv
load_dotenv()

from src.agents.financial_agent import FinancialAgent

agent = FinancialAgent()
result = agent.process_query("What was the Q4 revenue?")

print(result["response"])
print(f"Citations: {result['citations']}")
```

## Key Features Implemented

### 1. Retrieval with Improvements

- **Structure-aware chunking**: Preserves tables, respects sections
- **Hybrid search**: Semantic (vector) + Keyword (BM25)
- **Metadata filtering**: By document, date, section
- **Cross-encoder reranking**: Better top-k relevance
- **Citations**: Document name, page, section for every answer

### 2. Custom Tools

**Retrieval Tool**:
```python
result = retrieval_tool("What was the revenue?")
# Returns: context, citations, num_results
```

**Calculator Tool**:
```python
result = calculator_tool(
    operation="profit_margin",
    net_income=50_000_000,
    revenue=200_000_000
)
# Returns: 25.0%, with explanation and interpretation
```

**Vision Tool**:
```python
result = vision_tool(
    image_path="data/images/chart.png",
    query="What does this show?",
    analysis_type="chart"
)
# Returns: analysis of chart with extracted data
```

### 3. Agent Orchestration

**Workflow Planning**:
- Analyzes query to determine required tools
- Executes tools in appropriate order
- Synthesizes results with LLM

**State Management**:
- Tracks conversation history
- Maintains context across turns
- Logs all tool executions

### 4. Observability

**OpenTelemetry Integration**:
- Traces all operations
- Exports to Jaeger or Azure Monitor
- Tracks latency, errors, tool usage

**Start Jaeger** (Docker):
```powershell
docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

View traces at: http://localhost:16686

### 5. UI with Explainability

**Shows**:
- Chat interface
- Citations (expandable)
- Tool execution logs
- Session statistics
- Image upload capability

## Example Queries

### Simple Retrieval
```
"What was the total revenue for Q4 2023?"
```

### Calculation
```
"Calculate the profit margin if net income was $50M and revenue was $200M"
```

### Multi-step Reasoning
```
"Compare revenue growth between Q3 and Q4 2023"
```

### Vision Analysis
```
Upload: revenue_chart.png
Query: "What does this chart show?"
```

### Complex Query
```
"What were the key risk factors mentioned, and how might they impact the projected profit margin?"
```

## Evaluation Metrics

The system evaluates:

1. **Answer Quality**
   - Keyword coverage
   - Answer accuracy (for calculations)
   
2. **Citation Quality**
   - Presence of citations
   - Citation rate across queries

3. **Tool Usage**
   - Correct tool selection
   - Tool execution success

4. **Category Performance**
   - Factual retrieval
   - Calculations
   - Comparisons
   - Summarization

## Common Issues & Solutions

### Issue: "Search client not initialized"
**Solution**: Configure AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY in .env

### Issue: "Index not found"
**Solution**: Run document processor to create index:
```powershell
python -m src.ingestion.document_processor --input ./data/sample_pdfs
```

### Issue: No PDFs to process
**Solution**: Add sample PDFs to `data/sample_pdfs/`
- Download from investor relations sites
- Or create simple test PDFs

### Issue: Vision analysis fails
**Solution**: Ensure AZURE_OPENAI_VISION_DEPLOYMENT is configured and deployed

### Issue: High latency
**Solution**: 
- Use smaller top_k for retrieval
- Enable result caching
- Optimize chunk size

## Testing Checklist

- [ ] Environment configured (.env)
- [ ] Dependencies installed
- [ ] Azure services accessible
- [ ] Sample documents added
- [ ] Documents processed and indexed
- [ ] Streamlit UI loads
- [ ] Can ask questions and get responses
- [ ] Citations display correctly
- [ ] Tool calls are visible
- [ ] Image upload works
- [ ] Evaluation runs successfully
- [ ] Tracing exports to Jaeger (optional)

## Creating Your Golden Test Set

The default `evaluation/golden_set.json` is a template. To create a proper test set:

### Method 1: Interactive Generator (Recommended)

```powershell
# After adding and processing documents
python generate_golden_set.py
```

This will:
1. Test queries against your actual documents
2. Show you the agent's responses
3. Help you record expected answers
4. Generate a custom golden set

### Method 2: Manual Creation

1. Add documents and process them
2. Open Streamlit UI
3. Test queries and note the answers
4. Update `evaluation/golden_set.json` with actual expected values

Example entry:
```json
{
  "id": 1,
  "question": "What was the Q4 2023 revenue?",
  "expected_keywords": ["revenue", "220", "million", "Q4", "2023"],
  "expected_answer": "$220 million",
  "requires_retrieval": true,
  "category": "factual_retrieval"
}
```

## Next Steps for Production

1. **Security**
   - Add authentication (Azure AD)
   - Implement RBAC
   - Enable encryption

2. **Performance**
   - Add caching layer
   - Implement async processing
   - Optimize embeddings

3. **Monitoring**
   - Set up alerts
   - Create dashboards
   - Add health checks

4. **Scaling**
   - Move to stateless design
   - Add load balancing
   - Implement rate limiting

## Resources

- **Architecture**: [docs/architecture.md](docs/architecture.md)
- **Deployment**: [docs/deployment.md](docs/deployment.md)
- **Presentation**: [docs/PRESENTATION_GUIDE.md](docs/PRESENTATION_GUIDE.md)
- **Azure OpenAI**: https://learn.microsoft.com/azure/ai-services/openai/
- **Azure AI Search**: https://learn.microsoft.com/azure/search/

## Support

For issues or questions during the interview:
- Check the architecture docs
- Review example queries in README.md
- Consult error logs in terminal output
