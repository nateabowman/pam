"""
Correlation analysis between signals.
"""

import statistics
from typing import List, Dict
from logger import get_logger


class CorrelationAnalyzer:
    """Analyzes correlations between signals."""
    
    def __init__(self):
        self.logger = get_logger("correlation")
    
    def calculate_correlation(self, signal1: List[float], signal2: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient.
        
        Args:
            signal1: First signal values
            signal2: Second signal values
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(signal1) != len(signal2) or len(signal1) < 2:
            return 0.0
        
        mean1 = statistics.mean(signal1)
        mean2 = statistics.mean(signal2)
        
        numerator = sum((signal1[i] - mean1) * (signal2[i] - mean2) for i in range(len(signal1)))
        denom1 = sum((signal1[i] - mean1) ** 2 for i in range(len(signal1)))
        denom2 = sum((signal2[i] - mean2) ** 2 for i in range(len(signal2)))
        
        if denom1 == 0 or denom2 == 0:
            return 0.0
        
        correlation = numerator / (denom1 ** 0.5 * denom2 ** 0.5)
        return correlation
    
    def correlation_matrix(self, signals: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix for multiple signals.
        
        Args:
            signals: Dictionary of signal_name -> values
            
        Returns:
            Correlation matrix
        """
        matrix = {}
        signal_names = list(signals.keys())
        
        for i, name1 in enumerate(signal_names):
            matrix[name1] = {}
            for name2 in signal_names:
                if name1 == name2:
                    matrix[name1][name2] = 1.0
                else:
                    matrix[name1][name2] = self.calculate_correlation(
                        signals[name1],
                        signals[name2]
                    )
        
        return matrix

