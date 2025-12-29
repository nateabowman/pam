"""
Anomaly detection for signal patterns.
Detects unusual spikes or patterns in signal values.
"""

import statistics
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from logger import get_logger


class AnomalyDetector:
    """Detects anomalies in signal values over time."""
    
    def __init__(self, window_size: int = 30):
        """
        Initialize anomaly detector.
        
        Args:
            window_size: Number of historical values to consider
        """
        self.window_size = window_size
        self.logger = get_logger("anomaly_detector")
    
    def detect_anomaly(
        self,
        current_value: float,
        historical_values: List[float],
        threshold_std: float = 2.0
    ) -> Dict[str, Any]:
        """
        Detect if current value is anomalous.
        
        Args:
            current_value: Current signal value
            historical_values: List of historical values
            threshold_std: Number of standard deviations for threshold
            
        Returns:
            Dictionary with anomaly detection results
        """
        if not historical_values or len(historical_values) < 3:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'reason': 'insufficient_data'
            }
        
        # Calculate statistics
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0.0
        
        if stdev == 0:
            # All values are the same
            if current_value != mean:
                return {
                    'is_anomaly': True,
                    'score': abs(current_value - mean),
                    'reason': 'deviation_from_constant',
                    'mean': mean,
                    'current': current_value
                }
            return {
                'is_anomaly': False,
                'score': 0.0,
                'reason': 'normal'
            }
        
        # Calculate z-score
        z_score = (current_value - mean) / stdev
        
        is_anomaly = abs(z_score) > threshold_std
        
        return {
            'is_anomaly': is_anomaly,
            'score': abs(z_score),
            'z_score': z_score,
            'mean': mean,
            'stdev': stdev,
            'current': current_value,
            'threshold': threshold_std,
            'reason': 'statistical_outlier' if is_anomaly else 'normal'
        }
    
    def detect_spike(
        self,
        current_value: float,
        previous_value: float,
        spike_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Detect sudden spike in value.
        
        Args:
            current_value: Current signal value
            previous_value: Previous signal value
            spike_threshold: Minimum change to consider a spike
            
        Returns:
            Dictionary with spike detection results
        """
        change = current_value - previous_value
        change_percent = abs(change) / previous_value if previous_value > 0 else abs(change)
        
        is_spike = change_percent >= spike_threshold
        
        return {
            'is_spike': is_spike,
            'change': change,
            'change_percent': change_percent,
            'current': current_value,
            'previous': previous_value,
            'direction': 'up' if change > 0 else 'down'
        }
    
    def detect_trend(
        self,
        values: List[float],
        min_points: int = 5
    ) -> Dict[str, Any]:
        """
        Detect trend in values (increasing, decreasing, stable).
        
        Args:
            values: List of values over time
            min_points: Minimum number of points needed
            
        Returns:
            Dictionary with trend analysis
        """
        if len(values) < min_points:
            return {
                'trend': 'insufficient_data',
                'slope': 0.0,
                'strength': 0.0
            }
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine trend
        if slope > 0.01:
            trend = 'increasing'
        elif slope < -0.01:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Calculate strength (correlation-like)
        mean_y = sum_y / n
        ss_res = sum((values[i] - (slope * x[i] + (sum_y/n - slope * sum_x/n)))**2 for i in range(n))
        ss_tot = sum((values[i] - mean_y)**2 for i in range(n))
        strength = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return {
            'trend': trend,
            'slope': slope,
            'strength': abs(strength),
            'points': n
        }

