"""
Financial calculator tool for computing metrics and ratios.
Provides calculations for common financial metrics used in analysis.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal, InvalidOperation

from src.tracing.telemetry import get_telemetry, trace_function

logger = logging.getLogger(__name__)


class FinancialCalculator:
    """Performs financial calculations and metric computations."""
    
    def __init__(self):
        self.telemetry = get_telemetry()
    
    @trace_function("calculate_metric")
    def calculate(self, operation: str, **params) -> Dict[str, Any]:
        """
        Calculate financial metrics based on operation type.
        
        Supported operations:
        - profit_margin: (net_income, revenue)
        - gross_margin: (gross_profit, revenue)
        - operating_margin: (operating_income, revenue)
        - roe: Return on Equity (net_income, shareholders_equity)
        - roa: Return on Assets (net_income, total_assets)
        - current_ratio: (current_assets, current_liabilities)
        - debt_to_equity: (total_debt, total_equity)
        - pe_ratio: Price to Earnings (stock_price, earnings_per_share)
        - growth_rate: (current_value, previous_value)
        - eps: Earnings Per Share (net_income, shares_outstanding)
        
        Args:
            operation: Type of calculation
            **params: Required parameters for the operation
            
        Returns:
            Dictionary with result and explanation
        """
        try:
            # Map operations to calculation methods
            calculators = {
                "profit_margin": self._profit_margin,
                "gross_margin": self._gross_margin,
                "operating_margin": self._operating_margin,
                "roe": self._return_on_equity,
                "roa": self._return_on_assets,
                "current_ratio": self._current_ratio,
                "debt_to_equity": self._debt_to_equity,
                "pe_ratio": self._pe_ratio,
                "growth_rate": self._growth_rate,
                "eps": self._earnings_per_share,
            }
            
            if operation not in calculators:
                available = ", ".join(calculators.keys())
                return {
                    "error": f"Unknown operation '{operation}'. Available: {available}",
                    "success": False
                }
            
            # Execute calculation
            result = calculators[operation](**params)
            
            self.telemetry.add_event("calculation_completed", {
                "operation": operation,
                "result": result["value"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Calculation error for {operation}: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def _safe_divide(self, numerator: float, denominator: float) -> Optional[float]:
        """Safely divide two numbers, returning None if denominator is zero."""
        if denominator == 0:
            return None
        try:
            return Decimal(str(numerator)) / Decimal(str(denominator))
        except (InvalidOperation, TypeError):
            return None
    
    def _profit_margin(self, net_income: float, revenue: float) -> Dict[str, Any]:
        """Calculate profit margin (net income / revenue) * 100."""
        result = self._safe_divide(net_income, revenue)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        percentage = float(result) * 100
        return {
            "value": round(percentage, 2),
            "formatted": f"{percentage:.2f}%",
            "explanation": f"Profit Margin = (Net Income / Revenue) × 100 = ({net_income:,.2f} / {revenue:,.2f}) × 100",
            "interpretation": self._interpret_profit_margin(percentage),
            "success": True
        }
    
    def _gross_margin(self, gross_profit: float, revenue: float) -> Dict[str, Any]:
        """Calculate gross margin."""
        result = self._safe_divide(gross_profit, revenue)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        percentage = float(result) * 100
        return {
            "value": round(percentage, 2),
            "formatted": f"{percentage:.2f}%",
            "explanation": f"Gross Margin = (Gross Profit / Revenue) × 100 = ({gross_profit:,.2f} / {revenue:,.2f}) × 100",
            "success": True
        }
    
    def _operating_margin(self, operating_income: float, revenue: float) -> Dict[str, Any]:
        """Calculate operating margin."""
        result = self._safe_divide(operating_income, revenue)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        percentage = float(result) * 100
        return {
            "value": round(percentage, 2),
            "formatted": f"{percentage:.2f}%",
            "explanation": f"Operating Margin = (Operating Income / Revenue) × 100 = ({operating_income:,.2f} / {revenue:,.2f}) × 100",
            "success": True
        }
    
    def _return_on_equity(self, net_income: float, shareholders_equity: float) -> Dict[str, Any]:
        """Calculate Return on Equity (ROE)."""
        result = self._safe_divide(net_income, shareholders_equity)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        percentage = float(result) * 100
        return {
            "value": round(percentage, 2),
            "formatted": f"{percentage:.2f}%",
            "explanation": f"ROE = (Net Income / Shareholders' Equity) × 100 = ({net_income:,.2f} / {shareholders_equity:,.2f}) × 100",
            "success": True
        }
    
    def _return_on_assets(self, net_income: float, total_assets: float) -> Dict[str, Any]:
        """Calculate Return on Assets (ROA)."""
        result = self._safe_divide(net_income, total_assets)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        percentage = float(result) * 100
        return {
            "value": round(percentage, 2),
            "formatted": f"{percentage:.2f}%",
            "explanation": f"ROA = (Net Income / Total Assets) × 100 = ({net_income:,.2f} / {total_assets:,.2f}) × 100",
            "success": True
        }
    
    def _current_ratio(self, current_assets: float, current_liabilities: float) -> Dict[str, Any]:
        """Calculate current ratio."""
        result = self._safe_divide(current_assets, current_liabilities)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        ratio = float(result)
        return {
            "value": round(ratio, 2),
            "formatted": f"{ratio:.2f}",
            "explanation": f"Current Ratio = Current Assets / Current Liabilities = {current_assets:,.2f} / {current_liabilities:,.2f}",
            "interpretation": self._interpret_current_ratio(ratio),
            "success": True
        }
    
    def _debt_to_equity(self, total_debt: float, total_equity: float) -> Dict[str, Any]:
        """Calculate debt-to-equity ratio."""
        result = self._safe_divide(total_debt, total_equity)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        ratio = float(result)
        return {
            "value": round(ratio, 2),
            "formatted": f"{ratio:.2f}",
            "explanation": f"Debt-to-Equity = Total Debt / Total Equity = {total_debt:,.2f} / {total_equity:,.2f}",
            "success": True
        }
    
    def _pe_ratio(self, stock_price: float, earnings_per_share: float) -> Dict[str, Any]:
        """Calculate Price-to-Earnings ratio."""
        result = self._safe_divide(stock_price, earnings_per_share)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        ratio = float(result)
        return {
            "value": round(ratio, 2),
            "formatted": f"{ratio:.2f}",
            "explanation": f"P/E Ratio = Stock Price / Earnings Per Share = {stock_price:.2f} / {earnings_per_share:.2f}",
            "success": True
        }
    
    def _growth_rate(self, current_value: float, previous_value: float) -> Dict[str, Any]:
        """Calculate growth rate percentage."""
        if previous_value == 0:
            return {"error": "Previous value cannot be zero", "success": False}
        
        growth = ((current_value - previous_value) / previous_value) * 100
        return {
            "value": round(growth, 2),
            "formatted": f"{growth:+.2f}%",
            "explanation": f"Growth Rate = ((Current - Previous) / Previous) × 100 = (({current_value:,.2f} - {previous_value:,.2f}) / {previous_value:,.2f}) × 100",
            "success": True
        }
    
    def _earnings_per_share(self, net_income: float, shares_outstanding: float) -> Dict[str, Any]:
        """Calculate Earnings Per Share (EPS)."""
        result = self._safe_divide(net_income, shares_outstanding)
        if result is None:
            return {"error": "Invalid inputs or division by zero", "success": False}
        
        eps = float(result)
        return {
            "value": round(eps, 2),
            "formatted": f"${eps:.2f}",
            "explanation": f"EPS = Net Income / Shares Outstanding = {net_income:,.2f} / {shares_outstanding:,.0f}",
            "success": True
        }
    
    def _interpret_profit_margin(self, margin: float) -> str:
        """Provide interpretation of profit margin."""
        if margin < 0:
            return "Negative margin indicates losses"
        elif margin < 5:
            return "Low profit margin"
        elif margin < 10:
            return "Moderate profit margin"
        elif margin < 20:
            return "Good profit margin"
        else:
            return "Excellent profit margin"
    
    def _interpret_current_ratio(self, ratio: float) -> str:
        """Provide interpretation of current ratio."""
        if ratio < 1.0:
            return "May have liquidity issues (ratio < 1.0)"
        elif ratio < 1.5:
            return "Acceptable liquidity"
        elif ratio < 3.0:
            return "Good liquidity"
        else:
            return "Very strong liquidity (may indicate inefficient use of assets)"


class CalculatorTool:
    """Tool wrapper for agent integration."""
    
    def __init__(self):
        self.calculator = FinancialCalculator()
    
    @property
    def name(self) -> str:
        return "calculate_financial_metric"
    
    @property
    def description(self) -> str:
        return """Calculate financial metrics and ratios.
        
        Supported calculations:
        - profit_margin: Calculate profit margin (requires: net_income, revenue)
        - gross_margin: Calculate gross margin (requires: gross_profit, revenue)
        - operating_margin: Calculate operating margin (requires: operating_income, revenue)
        - roe: Return on Equity (requires: net_income, shareholders_equity)
        - roa: Return on Assets (requires: net_income, total_assets)
        - current_ratio: Current ratio (requires: current_assets, current_liabilities)
        - debt_to_equity: Debt-to-equity ratio (requires: total_debt, total_equity)
        - pe_ratio: Price-to-earnings ratio (requires: stock_price, earnings_per_share)
        - growth_rate: Growth rate percentage (requires: current_value, previous_value)
        - eps: Earnings per share (requires: net_income, shares_outstanding)
        
        Use this tool when you need to compute financial metrics from extracted data.
        """
    
    def __call__(self, operation: str, **params) -> Dict[str, Any]:
        """Execute the calculator tool."""
        return self.calculator.calculate(operation, **params)
