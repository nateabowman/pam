"""
NLP processing pipeline for World P.A.M.
Provides text preprocessing, tokenization, and basic NLP utilities.
"""

import re
from typing import List, Dict, Any, Optional
from logger import get_logger


class NLPProcessor:
    """Basic NLP processor for text preprocessing."""
    
    def __init__(self):
        self.logger = get_logger("nlp")
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for analysis.
        
        Args:
            text: Raw text input
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        
        return text.strip()
    
    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Input text
            min_length: Minimum keyword length
            
        Returns:
            List of keywords
        """
        text = self.preprocess_text(text)
        words = text.split()
        
        # Filter by length and remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
        
        keywords = [
            word for word in words
            if len(word) >= min_length and word not in stop_words
        ]
        
        return keywords
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple word overlap similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        words1 = set(self.extract_keywords(text1))
        words2 = set(self.extract_keywords(text2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def extract_phrases(self, text: str, min_words: int = 2, max_words: int = 4) -> List[str]:
        """
        Extract phrases (n-grams) from text.
        
        Args:
            text: Input text
            min_words: Minimum words in phrase
            max_words: Maximum words in phrase
            
        Returns:
            List of phrases
        """
        words = self.preprocess_text(text).split()
        phrases = []
        
        for n in range(min_words, max_words + 1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                if len(phrase) > 0:
                    phrases.append(phrase)
        
        return phrases

