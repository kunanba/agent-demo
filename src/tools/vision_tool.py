"""
Vision tool for analyzing financial charts and images using GPT-4 Vision.
Extracts data from charts, tables, and scanned documents.
"""

import os
import logging
import base64
from typing import Dict, Any, Optional, List
from pathlib import Path

from openai import AzureOpenAI
from PIL import Image

from src.tracing.telemetry import get_telemetry, trace_function

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """Analyzes financial images and charts using GPT-4 Vision."""
    
    def __init__(self):
        self.telemetry = get_telemetry()
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Use separate vision deployment if specified, otherwise use main deployment (GPT-4o/4-turbo are multimodal)
        self.vision_deployment = os.getenv(
            "AZURE_OPENAI_VISION_DEPLOYMENT",
            os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        )
    
    @trace_function("analyze_image")
    def analyze_image(
        self,
        image_path: str,
        query: Optional[str] = None,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze an image using GPT-4 Vision.
        
        Args:
            image_path: Path to image file
            query: Specific question about the image
            analysis_type: Type of analysis ('general', 'chart', 'table', 'extract_data')
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Validate image
            if not os.path.exists(image_path):
                return {
                    "error": f"Image not found: {image_path}",
                    "success": False
                }
            
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Build prompt based on analysis type
            prompt = self._build_prompt(analysis_type, query)
            
            # Call GPT-4 Vision
            with self.telemetry.trace_operation("vision_api_call", {
                "analysis_type": analysis_type,
                "image": Path(image_path).name
            }):
                response = self.client.chat.completions.create(
                    model=self.vision_deployment,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )
            
            analysis = response.choices[0].message.content
            
            return {
                "analysis": analysis,
                "image_path": image_path,
                "analysis_type": analysis_type,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _build_prompt(self, analysis_type: str, query: Optional[str] = None) -> str:
        """Build prompt based on analysis type."""
        prompts = {
            "general": "Analyze this financial image or chart. Describe what you see, including any key data points, trends, or insights.",
            
            "chart": """Analyze this financial chart or graph.
            
            Provide:
            1. Type of chart (line, bar, pie, etc.)
            2. What metrics are shown (axes labels, legend)
            3. Key data points and values
            4. Trends or patterns
            5. Any notable observations
            
            Format your response as structured data where possible.""",
            
            "table": """Extract data from this financial table or statement.
            
            Provide:
            1. Table structure (columns and rows)
            2. All numerical values with their labels
            3. Any totals or calculated fields
            4. Time periods if applicable
            
            Format as a structured table.""",
            
            "extract_data": """Extract all numerical data and financial metrics from this image.
            
            For each metric provide:
            - Metric name
            - Value
            - Unit (%, $, millions, etc.)
            - Time period if shown
            
            Be precise with numbers."""
        }
        
        base_prompt = prompts.get(analysis_type, prompts["general"])
        
        if query:
            base_prompt = f"{base_prompt}\n\nSpecific question: {query}"
        
        return base_prompt
    
    def analyze_multiple_images(
        self,
        image_paths: List[str],
        comparison_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze and compare multiple images.
        
        Useful for comparing charts across time periods or documents.
        """
        results = []
        
        for image_path in image_paths:
            result = self.analyze_image(
                image_path,
                query=comparison_query,
                analysis_type="extract_data"
            )
            results.append(result)
        
        # Create comparison summary
        if all(r.get("success") for r in results):
            comparison = self._generate_comparison(results)
            return {
                "individual_analyses": results,
                "comparison": comparison,
                "success": True
            }
        else:
            return {
                "individual_analyses": results,
                "error": "Some analyses failed",
                "success": False
            }
    
    def _generate_comparison(self, results: List[Dict[str, Any]]) -> str:
        """Generate a comparison summary from multiple analyses."""
        summaries = []
        for i, result in enumerate(results, 1):
            img_name = Path(result["image_path"]).name
            summaries.append(f"Image {i} ({img_name}):\n{result['analysis']}\n")
        
        comparison_prompt = f"""Based on these image analyses, provide a comparative summary:

{chr(10).join(summaries)}

Highlight:
1. Key differences
2. Trends across images
3. Notable changes in metrics
"""
        
        return comparison_prompt


class VisionTool:
    """Tool wrapper for agent integration."""
    
    def __init__(self):
        self.analyzer = VisionAnalyzer()
    
    @property
    def name(self) -> str:
        return "analyze_financial_image"
    
    @property
    def description(self) -> str:
        return """Analyze financial charts, graphs, tables, or scanned documents using vision AI.
        
        This tool can:
        - Extract data from charts and graphs
        - Read tables and financial statements from images
        - Analyze trends in visual data
        - Compare multiple charts
        
        Input parameters:
        - image_path: Path to the image file (required)
        - query: Specific question about the image (optional)
        - analysis_type: Type of analysis - 'general', 'chart', 'table', or 'extract_data' (default: 'general')
        
        Use this when the user asks about charts, provides images, or needs to extract data from visual content.
        """
    
    def __call__(
        self,
        image_path: str,
        query: Optional[str] = None,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """Execute the vision analysis tool."""
        return self.analyzer.analyze_image(image_path, query, analysis_type)
