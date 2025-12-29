"""
Time series analysis for signal and hypothesis data.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import statistics
from logger import get_logger


class TimeSeriesAnalyzer:
    """Analyzes time series data."""
    
    def __init__(self):
        self.logger = get_logger("time_series")
    
    def calculate_trend(self, values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """
        Calculate trend in time series.
        
        Args:
            values: List of values
            timestamps: List of timestamps
            
        Returns:
            Trend analysis results
        """
        if len(values) < 2:
            return {"trend": "insufficient_data", "slope": 0.0}
        
        # Simple linear regression
        n = len(values)
        x = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0.0
        
        if slope > 0.001:
            trend = "increasing"
        elif slope < -0.001:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": slope,
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0
        }
    
    def forecast(self, values: List[float], periods: int = 7) -> List[float]:
        """
        Simple moving average forecast.
        
        Args:
            values: Historical values
            periods: Number of periods to forecast
            
        Returns:
            Forecasted values
        """
        if not values:
            return [0.0] * periods
        
        # Use last N values for moving average
        window = min(7, len(values))
        recent = values[-window:]
        avg = statistics.mean(recent)
        
        return [avg] * periods

