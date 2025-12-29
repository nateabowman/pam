"""
Sentiment analysis for feed items.
Uses rule-based sentiment analysis (VADER-like) for simplicity.
"""

import re
from typing import Dict, Any
from logger import get_logger


class SentimentAnalyzer:
    """Rule-based sentiment analyzer."""
    
    # Positive and negative word lists (simplified)
    POSITIVE_WORDS = {
        'peace', 'agreement', 'treaty', 'cooperation', 'diplomacy', 'stability',
        'progress', 'success', 'improvement', 'resolution', 'ceasefire', 'truce',
        'dialogue', 'negotiation', 'compromise', 'unity', 'reconciliation'
    }
    
    NEGATIVE_WORDS = {
        'war', 'conflict', 'violence', 'attack', 'crisis', 'tension', 'threat',
        'sanctions', 'breakdown', 'collapse', 'coup', 'riot', 'protest', 'strike',
        'escalation', 'hostility', 'aggression', 'military', 'weapons', 'nuclear'
    }
    
    INTENSIFIERS = {
        'very', 'extremely', 'highly', 'severely', 'critically', 'massively',
        'significantly', 'substantially', 'dramatically'
    }
    
    NEGATORS = {'not', 'no', 'never', 'none', 'neither', 'nobody', 'nothing'}
    
    def __init__(self):
        self.logger = get_logger("sentiment")
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores and label
        """
        if not text:
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'label': 'neutral'
            }
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_score = 0.0
        negative_score = 0.0
        
        for i, word in enumerate(words):
            # Check for negators
            negated = False
            if i > 0 and words[i-1] in self.NEGATORS:
                negated = True
            
            # Check for intensifiers
            intensified = False
            if i > 0 and words[i-1] in self.INTENSIFIERS:
                intensified = True
            
            # Score words
            if word in self.POSITIVE_WORDS:
                score = 1.0
                if negated:
                    score = -0.5
                elif intensified:
                    score = 1.5
                positive_score += score
            
            elif word in self.NEGATIVE_WORDS:
                score = -1.0
                if negated:
                    score = 0.5
                elif intensified:
                    score = -1.5
                negative_score += score
        
        # Normalize scores
        total_words = len(words)
        if total_words > 0:
            positive_score = positive_score / total_words
            negative_score = negative_score / total_words
        
        # Calculate compound score
        compound = positive_score + negative_score
        
        # Normalize to -1 to 1 range
        compound = max(-1.0, min(1.0, compound))
        
        # Determine label
        if compound > 0.1:
            label = 'positive'
        elif compound < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'compound': compound,
            'positive': max(0.0, positive_score),
            'negative': abs(min(0.0, negative_score)),
            'neutral': 1.0 - abs(compound),
            'label': label
        }
    
    def get_sentiment_weight(self, text: str) -> float:
        """
        Get sentiment weight for signal computation.
        Negative sentiment increases weight, positive decreases.
        
        Args:
            text: Text to analyze
            
        Returns:
            Weight multiplier (0.5 to 1.5)
        """
        sentiment = self.analyze(text)
        compound = sentiment['compound']
        
        # Map compound score (-1 to 1) to weight (0.5 to 1.5)
        # Negative sentiment -> higher weight
        # Positive sentiment -> lower weight
        weight = 1.0 - (compound * 0.5)
        return max(0.5, min(1.5, weight))

