"""
Quick start script for setting up and running the Financial Agent.
"""

import os
import sys
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "="*60)
    print(text.center(60))
    print("="*60 + "\n")


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    if not env_path.exists():
        print("WARNING: .env file not found!")
        print("\nPlease create a .env file with your Azure credentials:")
        print("  cp .env.example .env")
        print("  # Then edit .env with your actual values\n")
        return False
    return True


def check_dependencies():
    """Check if dependencies are installed."""
    try:
        import streamlit
        import openai
        import azure.search.documents
        print("Dependencies check: OK")
        return True
    except ImportError as e:
        print(f"ERROR: Missing dependencies - {e}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt\n")
        return False


def check_azure_config():
    """Check Azure configuration."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("\nPlease configure these in your .env file\n")
        return False
    
    print("Azure configuration: OK")
    return True


def setup_directories():
    """Create necessary directories."""
    dirs = [
        "data/sample_pdfs",
        "data/images",
        "data/uploads",
        "logs",
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("Directory structure: OK")
    return True


def main():
    """Run setup checks and start options."""
    print_header("Financial Document Analysis Agent")
    print("Quick Start Script\n")
    
    # Run checks
    checks_passed = True
    
    print("Running pre-flight checks...\n")
    
    if not check_env_file():
        checks_passed = False
    
    if not check_dependencies():
        checks_passed = False
    
    if checks_passed and not check_azure_config():
        checks_passed = False
    
    setup_directories()
    
    if not checks_passed:
        print("\n" + "!"*60)
        print("Setup incomplete - please fix the issues above")
        print("!"*60 + "\n")
        sys.exit(1)
    
    print("\n" + "✓"*60)
    print("All checks passed! Your environment is ready.")
    print("✓"*60 + "\n")
    
    # Display options
    print("What would you like to do?\n")
    print("1. Run Streamlit UI (recommended for demo)")
    print("   Command: streamlit run src/ui/app.py")
    print()
    print("2. Process sample documents")
    print("   Command: python -m src.ingestion.document_processor --input ./data/sample_pdfs")
    print()
    print("3. Run evaluation")
    print("   Command: python -m evaluation.eval_script")
    print()
    print("4. Start Jaeger for tracing (Docker required)")
    print("   Command: docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest")
    print()
    
    print("\n" + "="*60)
    print("For detailed instructions, see README.md")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
