"""
Golden Set Generator

This script helps you create an evaluation golden set based on actual documents.

Usage:
1. Add sample PDFs to data/sample_pdfs/
2. Process them: python -m src.ingestion.document_processor --input ./data/sample_pdfs
3. Run this script: python generate_golden_set.py
4. Manually test each query in the UI
5. Update the golden_set.json with actual expected answers
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.agents.financial_agent import FinancialAgent


def generate_test_queries_template():
    """
    Generate a template of test queries that you should verify against your actual documents.
    """
    
    template_queries = [
        {
            "category": "factual_retrieval",
            "question": "What was the total revenue for [YOUR ACTUAL QUARTER/YEAR]?",
            "instructions": "Replace with actual quarter from your documents. After getting the answer, add it to 'expected_answer' or 'expected_keywords'",
            "requires_retrieval": True,
            "requires_calculation": False
        },
        {
            "category": "calculation",
            "question": "Calculate the profit margin if net income was $50 million and revenue was $200 million.",
            "expected_answer": "25%",
            "instructions": "This is a pure calculation - answer should always be 25%",
            "requires_retrieval": False,
            "requires_calculation": True
        },
        {
            "category": "factual_retrieval",
            "question": "What were the main risk factors mentioned?",
            "instructions": "After running against your docs, list the actual risk factors as expected_keywords",
            "requires_retrieval": True,
            "requires_calculation": False
        },
        {
            "category": "comparison",
            "question": "Compare revenue between [PERIOD 1] and [PERIOD 2]",
            "instructions": "Replace with actual periods from your documents",
            "requires_retrieval": True,
            "requires_calculation": True
        },
        {
            "category": "factual_retrieval",
            "question": "What were the operating expenses?",
            "instructions": "After running, add the actual value to expected_keywords",
            "requires_retrieval": True,
            "requires_calculation": False
        },
        {
            "category": "calculation",
            "question": "What is the current ratio if current assets are $150M and current liabilities are $100M?",
            "expected_answer": "1.5",
            "instructions": "Pure calculation - answer is always 1.5",
            "requires_retrieval": False,
            "requires_calculation": True
        },
        {
            "category": "factual_retrieval",
            "question": "Which business segments contributed most to revenue?",
            "instructions": "Add actual segment names from your docs to expected_keywords",
            "requires_retrieval": True,
            "requires_calculation": False
        },
        {
            "category": "calculation",
            "question": "What is the growth rate from $180M to $220M?",
            "expected_answer": "22.22%",
            "instructions": "Pure calculation",
            "requires_retrieval": False,
            "requires_calculation": True
        },
        {
            "category": "summarization",
            "question": "Summarize the key financial highlights",
            "instructions": "After running, add key terms that should appear in the summary",
            "requires_retrieval": True,
            "requires_calculation": False
        },
        {
            "category": "vision",
            "question": "What trends are shown in this revenue chart?",
            "instructions": "Upload a chart from data/images/ and document the expected trend description",
            "requires_retrieval": False,
            "requires_calculation": False,
            "requires_vision": True
        }
    ]
    
    return template_queries


def test_query_interactively(agent, query_data, query_num, total):
    """Test a single query and help user create the golden set entry."""
    
    print("\n" + "="*70)
    print(f"Query {query_num}/{total}")
    print("="*70)
    print(f"\nCategory: {query_data['category']}")
    print(f"Question: {query_data['question']}")
    print(f"\nInstructions: {query_data.get('instructions', 'N/A')}")
    print("\n" + "-"*70)
    
    # Check if this has a pre-defined answer (calculations)
    if "expected_answer" in query_data:
        print(f"Expected Answer (pre-defined): {query_data['expected_answer']}")
        return query_data
    
    # Ask if user wants to test this query
    response = input("\nTest this query against your documents? (y/n/skip): ").lower()
    
    if response == 'skip' or response == 's':
        print("Skipped")
        return None
    
    if response != 'y':
        return query_data
    
    print("\nQuerying agent...")
    try:
        result = agent.process_query(query_data['question'])
        
        print("\n" + "="*70)
        print("AGENT RESPONSE:")
        print("="*70)
        print(result.get('response', 'No response'))
        
        if result.get('citations'):
            print("\nCitations:")
            for cit in result['citations']:
                print(f"  - {cit['document']}, Page {cit['page']}")
        
        print("\n" + "-"*70)
        
        # Ask user to provide expected keywords or answer
        print("\nBased on the response above:")
        keywords_input = input("Enter expected keywords (comma-separated) or press Enter to skip: ")
        
        if keywords_input.strip():
            keywords = [k.strip() for k in keywords_input.split(',')]
            query_data['expected_keywords'] = keywords
        
        answer_input = input("Enter expected answer (or press Enter to skip): ")
        if answer_input.strip():
            query_data['expected_answer'] = answer_input.strip()
        
    except Exception as e:
        print(f"\nError testing query: {e}")
        print("You can manually test this in the UI later")
    
    return query_data


def main():
    """Interactive golden set generator."""
    
    print("\n" + "="*70)
    print(" GOLDEN SET GENERATOR ".center(70))
    print("="*70)
    print("\nThis tool helps you create a golden test set from your actual documents.")
    print("\nPrerequisites:")
    print("1. Sample PDFs in data/sample_pdfs/")
    print("2. Documents processed and indexed")
    print("3. Azure OpenAI configured in .env")
    print("\n" + "="*70)
    
    # Check if documents exist
    pdf_dir = Path("data/sample_pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    
    if not pdf_files:
        print("\nWARNING: No PDF files found in data/sample_pdfs/")
        print("Please add sample documents before running this script.")
        return
    
    print(f"\nFound {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    
    # Ask if ready to proceed
    proceed = input("\nProceed with golden set generation? (y/n): ").lower()
    if proceed != 'y':
        print("Cancelled")
        return
    
    # Initialize agent
    print("\nInitializing agent...")
    try:
        agent = FinancialAgent()
    except Exception as e:
        print(f"\nError initializing agent: {e}")
        print("Make sure your .env is configured and Azure services are accessible")
        return
    
    # Generate template queries
    template_queries = generate_test_queries_template()
    
    # Test each query
    golden_set = []
    
    print("\n" + "="*70)
    print("INTERACTIVE QUERY TESTING")
    print("="*70)
    print("\nFor each query, you can:")
    print("  - Test it against your actual documents")
    print("  - See the agent's response")
    print("  - Define expected keywords or answers")
    print("  - Skip queries you want to handle manually")
    
    for i, query_data in enumerate(template_queries, 1):
        result = test_query_interactively(agent, query_data, i, len(template_queries))
        
        if result:
            result['id'] = i
            golden_set.append(result)
        
        # Reset agent between queries
        agent.reset_conversation()
    
    # Save golden set
    output_path = Path("evaluation/golden_set.json")
    
    with open(output_path, 'w') as f:
        json.dump(golden_set, f, indent=2)
    
    print("\n" + "="*70)
    print(f"Golden set saved to {output_path}")
    print(f"Total queries: {len(golden_set)}")
    print("="*70)
    print("\nNext steps:")
    print("1. Review evaluation/golden_set.json")
    print("2. Add any missing expected_keywords or expected_answer fields")
    print("3. Add more queries specific to your documents")
    print("4. Run evaluation: python -m evaluation.eval_script")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
