"""
Evaluation script for the Financial Document Analysis Agent.
Tests accuracy, citation quality, and tool usage against a golden set using custom evaluators.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.agents.financial_agent import FinancialAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentEvaluator:
    """Evaluates agent performance against a golden test set using custom metrics."""
    
    def __init__(self, golden_set_path: str):
        self.golden_set_path = golden_set_path
        self.agent = FinancialAgent()
        self.results = []
        logger.info("Using custom evaluation metrics")
    
    def load_golden_set(self) -> List[Dict[str, Any]]:
        """Load the golden test set."""
        with open(self.golden_set_path, 'r') as f:
            return json.load(f)
    
    def evaluate_answer(
        self,
        question: Dict[str, Any],
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single answer using custom metrics.
        
        Evaluates:
        1. Answer presence and success
        2. Keyword/expected answer matching
        3. Citation quality
        4. Tool usage correctness
        5. Response completeness
        """
        evaluation = {
            "question_id": question["id"],
            "question": question["question"],
            "category": question["category"],
            "success": response.get("success", False),
            "has_response": bool(response.get("response")),
            "scores": {}
        }
        
        answer = response.get("response", "")
        
        # 1. Check expected keywords (for factual questions)
        if "expected_keywords" in question and question["expected_keywords"]:
            keywords = question["expected_keywords"]
            answer_lower = answer.lower()
            matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
            keyword_score = matches / len(keywords) if keywords else 0
            evaluation["scores"]["keyword_match"] = round(keyword_score, 2)
        
        # 2. Check expected answer matching (for calculations and specific facts)
        if "expected_answer" in question and question["expected_answer"]:
            expected = str(question["expected_answer"]).lower()
            # Check if key parts of expected answer appear
            if expected in answer.lower():
                evaluation["scores"]["answer_match"] = 1.0
            else:
                # Partial credit for numbers/values appearing
                import re
                expected_numbers = re.findall(r'\d+\.?\d*', expected)
                answer_numbers = re.findall(r'\d+\.?\d*', answer)
                if expected_numbers and any(num in answer_numbers for num in expected_numbers):
                    evaluation["scores"]["answer_match"] = 0.5
                else:
                    evaluation["scores"]["answer_match"] = 0.0
        
        # 3. Citation quality
        citations = response.get("citations", [])
        if question.get("requires_retrieval", False):
            # For retrieval questions, citations are required
            evaluation["scores"]["citation_quality"] = 1.0 if citations else 0.0
        evaluation["num_citations"] = len(citations)
        
        # 4. Tool usage correctness
        tool_calls = response.get("tool_calls", [])
        evaluation["num_tool_calls"] = len(tool_calls)
        
        if question.get("requires_retrieval"):
            used_retrieval = any(
                "search" in tc.get("tool", "").lower()
                for tc in tool_calls
            )
            evaluation["scores"]["tool_retrieval"] = 1.0 if used_retrieval else 0.0
        
        if question.get("requires_calculation"):
            used_calculator = any(
                "calculate" in tc.get("tool", "").lower()
                for tc in tool_calls
            )
            evaluation["scores"]["tool_calculator"] = 1.0 if used_calculator else 0.0
        
        if question.get("requires_vision"):
            used_vision = any(
                "vision" in tc.get("tool", "").lower() or "image" in tc.get("tool", "").lower()
                for tc in tool_calls
            )
            evaluation["scores"]["tool_vision"] = 1.0 if used_vision else 0.0
        
        # 5. Response completeness (has meaningful content)
        if answer and len(answer.strip()) > 20:
            evaluation["scores"]["response_completeness"] = 1.0
        elif answer:
            evaluation["scores"]["response_completeness"] = 0.5
        else:
            evaluation["scores"]["response_completeness"] = 0.0
        
        # Calculate overall score from all metrics
        scores = evaluation["scores"]
        if scores:
            evaluation["overall_score"] = round(sum(scores.values()) / len(scores), 2)
        else:
            evaluation["overall_score"] = 0.0
        
        return evaluation
    
    def run_evaluation(self) -> Dict[str, Any]:
        """Run full evaluation on the golden set."""
        logger.info("Starting evaluation...")
        
        golden_set = self.load_golden_set()
        
        for i, question in enumerate(golden_set, 1):
            logger.info(f"Evaluating question {i}/{len(golden_set)}: {question['question']}")
            
            try:
                # Get agent response
                response = self.agent.process_query(question["question"])
                
                # Evaluate response
                eval_result = self.evaluate_answer(question, response)
                eval_result["response_preview"] = response.get("response", "")[:200]
                
                self.results.append(eval_result)
                
                logger.info(f"Score: {eval_result['overall_score']}")
                
            except Exception as e:
                logger.error(f"Error evaluating question {question['id']}: {e}")
                self.results.append({
                    "question_id": question["id"],
                    "question": question["question"],
                    "success": False,
                    "error": str(e),
                    "overall_score": 0.0
                })
            
            # Reset agent between questions
            self.agent.reset_conversation()
        
        # Calculate aggregate metrics
        aggregate = self._calculate_aggregate_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(golden_set),
            "results": self.results,
            "aggregate_metrics": aggregate
        }
    
    def _calculate_aggregate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate evaluation metrics."""
        if not self.results:
            return {}
        
        successful = [r for r in self.results if r.get("success")]
        
        # Overall scores
        overall_scores = [r.get("overall_score", 0) for r in self.results]
        avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        
        # Individual metric aggregates
        metric_names = ["keyword_match", "answer_match", "citation_quality", 
                       "tool_retrieval", "tool_calculator", "tool_vision", 
                       "response_completeness"]
        metric_aggregates = {}
        
        for metric in metric_names:
            scores = [
                r.get("scores", {}).get(metric, 0) 
                for r in self.results 
                if metric in r.get("scores", {})
            ]
            if scores:
                metric_aggregates[metric] = round(sum(scores) / len(scores), 2)
        
        # Citation metrics
        with_citations = sum(1 for r in self.results if r.get("num_citations", 0) > 0)
        citation_rate = with_citations / len(self.results)
        
        # Tool usage metrics
        total_tool_calls = sum(r.get("num_tool_calls", 0) for r in self.results)
        avg_tools_per_query = total_tool_calls / len(self.results)
        
        # Category performance
        category_scores = {}
        for result in self.results:
            category = result.get("category", "unknown")
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(result.get("overall_score", 0))
        
        category_averages = {
            cat: round(sum(scores) / len(scores), 2)
            for cat, scores in category_scores.items()
        }
        
        return {
            "success_rate": round(len(successful) / len(self.results), 2),
            "average_score": round(avg_score, 2),
            "individual_metrics": metric_aggregates,
            "citation_rate": round(citation_rate, 2),
            "avg_tools_per_query": round(avg_tools_per_query, 2),
            "category_performance": category_averages,
            "total_successful": len(successful),
            "total_failed": len(self.results) - len(successful)
        }
    
    def save_results(self, output_path: str):
        """Save evaluation results to JSON file."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(self.results),
            "results": self.results,
            "aggregate_metrics": self._calculate_aggregate_metrics()
        }
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
    
    def print_summary(self):
        """Print evaluation summary to console."""
        aggregate = self._calculate_aggregate_metrics()
        
        print("\n" + "="*70)
        print("FINANCIAL AGENT EVALUATION SUMMARY")
        print("="*70)
        print(f"Total Questions:     {len(self.results)}")
        print(f"Successful:          {aggregate['total_successful']}")
        print(f"Failed:              {aggregate['total_failed']}")
        print(f"Success Rate:        {aggregate['success_rate']*100:.1f}%")
        print(f"Average Score:       {aggregate['average_score']:.2f}/1.0")
        print(f"Citation Rate:       {aggregate['citation_rate']*100:.1f}%")
        print(f"Avg Tools/Query:     {aggregate['avg_tools_per_query']:.1f}")
        
        print("\nCustom Evaluation Metrics:")
        individual_metrics = aggregate.get("individual_metrics", {})
        if individual_metrics:
            for metric, value in sorted(individual_metrics.items()):
                metric_display = metric.replace("_", " ").title()
                print(f"  {metric_display:30s}: {value:.2f}/1.0")
        else:
            print("  No detailed metrics available")
        
        print("\nCategory Performance:")
        for category, score in sorted(aggregate["category_performance"].items()):
            print(f"  {category:20s}: {score:.2f}/1.0")
        print("="*70 + "\n")


def main():
    """Run evaluation."""
    golden_set_path = Path(__file__).parent / "golden_set.json"
    output_path = Path(__file__).parent / "results.json"
    
    evaluator = AgentEvaluator(str(golden_set_path))
    
    # Run evaluation
    results = evaluator.run_evaluation()
    
    # Save results
    evaluator.save_results(str(output_path))
    
    # Print summary
    evaluator.print_summary()


if __name__ == "__main__":
    main()
