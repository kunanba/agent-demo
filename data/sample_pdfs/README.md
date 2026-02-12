# Sample Financial Documents

This directory contains sample financial documents for testing the agent.

For the demo, you should add:

1. **Quarterly/Annual Reports (PDFs)**
   - Example: Q4_2023_Earnings.pdf
   - Include: Revenue, expenses, balance sheet, cash flow
   - Can use public reports from companies like Apple, Microsoft, etc.

2. **Financial Charts/Images**
   - Revenue trend charts
   - Profit margin graphs
   - Market share visualizations

## How to Add Sample Documents

### Option 1: Download Public Reports

Many companies publish investor reports:
- Apple: https://investor.apple.com/
- Microsoft: https://www.microsoft.com/en-us/Investor
- Tesla: https://ir.tesla.com/

Download their quarterly (10-Q) or annual (10-K) reports.

### Option 2: Create Mock Reports

For a quick demo, create simple PDFs with:

```
ACME Corporation
Q4 2023 Financial Report

EXECUTIVE SUMMARY
Total revenue for Q4 2023 was $220 million, representing 
15% growth year-over-year.

REVENUE BREAKDOWN
Product Sales: $150 million
Service Revenue: $70 million

EXPENSES
Operating Expenses: $120 million
Cost of Goods Sold: $60 million

NET INCOME
Net Income: $40 million
Profit Margin: 18.2%
```

### Processing Documents

Once you have PDFs in this directory:

```bash
python -m src.ingestion.document_processor --input ./data/sample_pdfs
```

This will:
1. Extract text from PDFs
2. Create structure-aware chunks
3. Generate embeddings
4. Index in Azure AI Search

## Sample Image Files

Place financial charts and graphs in `data/images/`:
- revenue_chart.png
- profit_margins.jpg
- balance_sheet_table.png

Use these with the vision tool for image analysis.
