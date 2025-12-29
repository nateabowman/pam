"""
ML-based signal weight optimization.
Uses historical data to optimize signal weights.
"""

import statistics
from typing import List, Dict, Any, Optional
from logger import get_logger


class SignalOptimizer:
    """Optimizes signal weights based on historical performance."""
    
    def __init__(self):
        self.logger = get_logger("signal_optimizer")
    
    def calculate_correlation(
        self,
        signal_values: List[float],
        outcome_values: List[float]
    ) -> float:
        """
        Calculate correlation between signal and outcome.
        
        Args:
            signal_values: Historical signal values
            outcome_values: Historical outcome values (0 or 1)
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(signal_values) != len(outcome_values) or len(signal_values) < 2:
            return 0.0
        
        # Calculate means
        mean_signal = statistics.mean(signal_values)
        mean_outcome = statistics.mean(outcome_values)
        
        # Calculate covariance and variances
        covariance = sum(
            (signal_values[i] - mean_signal) * (outcome_values[i] - mean_outcome)
            for i in range(len(signal_values))
        ) / len(signal_values)
        
        var_signal = statistics.variance(signal_values) if len(signal_values) > 1 else 0.0
        var_outcome = statistics.variance(outcome_values) if len(outcome_values) > 1 else 0.0
        
        if var_signal == 0 or var_outcome == 0:
            return 0.0
        
        # Correlation coefficient
        correlation = covariance / (statistics.stdev(signal_values) * statistics.stdev(outcome_values))
        
        return correlation
    
    def optimize_weight(
        self,
        signal_name: str,
        signal_values: List[float],
        outcome_values: List[float],
        current_weight: float
    ) -> float:
        """
        Optimize signal weight based on correlation with outcomes.
        
        Args:
            signal_name: Name of the signal
            signal_values: Historical signal values
            outcome_values: Historical outcome values
            current_weight: Current weight
            
        Returns:
            Optimized weight
        """
        correlation = self.calculate_correlation(signal_values, outcome_values)
        
        # Adjust weight based on correlation
        # Positive correlation -> increase weight
        # Negative correlation -> decrease weight (or flip sign)
        # Weak correlation -> reduce weight
        
        if abs(correlation) < 0.1:
            # Weak correlation, reduce weight
            optimized = current_weight * 0.5
        elif correlation > 0:
            # Positive correlation, increase weight proportionally
            optimized = current_weight * (1 + correlation)
        else:
            # Negative correlation, could indicate inverse relationship
            # For now, reduce weight
            optimized = current_weight * (1 + correlation)
        
        # Keep weight in reasonable range
        optimized = max(-5.0, min(5.0, optimized))
        
        self.logger.info(
            f"Optimized weight for {signal_name}: {current_weight:.2f} -> {optimized:.2f} "
            f"(correlation: {correlation:.3f})"
        )
        
        return optimized
    
    def analyze_signal_performance(
        self,
        signal_name: str,
        signal_values: List[float],
        outcome_values: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze signal performance metrics.
        
        Args:
            signal_name: Name of the signal
            signal_values: Historical signal values
            outcome_values: Historical outcome values
            
        Returns:
            Dictionary with performance metrics
        """
        if len(signal_values) != len(outcome_values) or len(signal_values) < 2:
            return {
                'correlation': 0.0,
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'insufficient_data': True
            }
        
        correlation = self.calculate_correlation(signal_values, outcome_values)
        
        # Calculate accuracy metrics (using threshold of 0.5 for signal)
        true_positives = sum(
            1 for i in range(len(signal_values))
            if signal_values[i] > 0.5 and outcome_values[i] > 0.5
        )
        true_negatives = sum(
            1 for i in range(len(signal_values))
            if signal_values[i] <= 0.5 and outcome_values[i] <= 0.5
        )
        false_positives = sum(
            1 for i in range(len(signal_values))
            if signal_values[i] > 0.5 and outcome_values[i] <= 0.5
        )
        false_negatives = sum(
            1 for i in range(len(signal_values))
            if signal_values[i] <= 0.5 and outcome_values[i] > 0.5
        )
        
        total = len(signal_values)
        accuracy = (true_positives + true_negatives) / total if total > 0 else 0.0
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        return {
            'correlation': correlation,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'true_positives': true_positives,
            'true_negatives': true_negatives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'insufficient_data': False
        }

