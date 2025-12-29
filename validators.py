"""
Configuration validation for World P.A.M.
Validates config schema, references, and data integrity.
"""

from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass
import datetime
import re


class ValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_config(config: Any) -> List[str]:
    """
    Validate configuration structure and references.
    
    Args:
        config: Config object with sources, signals, hypotheses, etc.
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []
    
    # Validate sources
    source_names: Set[str] = set()
    for source in config.sources:
        if not source.name:
            errors.append("Source missing name")
        elif source.name in source_names:
            errors.append(f"Duplicate source name: {source.name}")
        else:
            source_names.add(source.name)
        
        if not source.url:
            errors.append(f"Source '{source.name}' missing URL")
        
        if source.type not in ("rss", "atom"):
            errors.append(f"Source '{source.name}' has invalid type: {source.type}")
        
        if source.timeout <= 0:
            errors.append(f"Source '{source.name}' has invalid timeout: {source.timeout}")
    
    # Validate signals
    signal_names: Set[str] = set()
    for signal in config.signals:
        if not signal.name:
            errors.append("Signal missing name")
        elif signal.name in signal_names:
            errors.append(f"Duplicate signal name: {signal.name}")
        else:
            signal_names.add(signal.name)
        
        if signal.aggregation not in ("sum", "max"):
            errors.append(f"Signal '{signal.name}' has invalid aggregation: {signal.aggregation}")
        
        if signal.cap <= 0:
            errors.append(f"Signal '{signal.name}' has invalid cap: {signal.cap}")
    
    # Validate hypotheses
    hypothesis_names: Set[str] = set()
    for hypothesis in config.hypotheses:
        if not hypothesis.name:
            errors.append("Hypothesis missing name")
        elif hypothesis.name in hypothesis_names:
            errors.append(f"Duplicate hypothesis name: {hypothesis.name}")
        else:
            hypothesis_names.add(hypothesis.name)
        
        if not (0 <= hypothesis.prior <= 1):
            errors.append(f"Hypothesis '{hypothesis.name}' has invalid prior: {hypothesis.prior}")
        
        # Check signal references
        for signal_name in hypothesis.signals:
            if signal_name not in signal_names:
                errors.append(f"Hypothesis '{hypothesis.name}' references unknown signal: {signal_name}")
    
    # Validate keyword sets
    keyword_set_names: Set[str] = set(config.keyword_sets.keys())
    
    # Validate signal bindings
    for signal_name, binding in config.signal_bindings.items():
        if signal_name not in signal_names:
            errors.append(f"Signal binding for unknown signal: {signal_name}")
        
        sources = binding.get("sources", [])
        for source_name in sources:
            if source_name not in source_names:
                errors.append(f"Signal binding '{signal_name}' references unknown source: {source_name}")
        
        keywords = binding.get("keywords", [])
        for keyword_set_name in keywords:
            if keyword_set_name not in keyword_set_names:
                errors.append(f"Signal binding '{signal_name}' references unknown keyword set: {keyword_set_name}")
        
        window_days = binding.get("window_days", 7)
        if not isinstance(window_days, (int, float)) or window_days <= 0:
            errors.append(f"Signal binding '{signal_name}' has invalid window_days: {window_days}")
    
    return errors


def parse_date(date_str: str, window_days: int = 7) -> Optional[datetime.datetime]:
    """
    Parse date string with multiple fallback strategies.
    
    Args:
        date_str: Date string to parse
        window_days: Number of days in the window (for relative parsing)
        
    Returns:
        Parsed datetime or None if unparseable
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Try common RSS/Atom date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822 with timezone
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
        "%a, %d %b %Y %H:%M:%S",     # RFC 822 without timezone
        "%Y-%m-%dT%H:%M:%S%z",        # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
        "%Y-%m-%dT%H:%M:%S",         # ISO 8601 without timezone
        "%Y-%m-%d %H:%M:%S",         # Simple format
        "%Y-%m-%d",                  # Date only
        "%d %b %Y",                  # Day Month Year
        "%b %d, %Y",                 # Month Day, Year
    ]
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            # If no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        except ValueError:
            continue
    
    # Try to extract year and month from string
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    month_names = {
        'jan', 'feb', 'mar', 'apr', 'may', 'jun',
        'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
    }
    
    if year_match:
        # Found a year, try to parse more
        try:
            # Use dateutil-like parsing (simplified)
            # Just check if it's within window
            # For now, if we find a year, assume it's recent enough
            year = int(year_match.group())
            current_year = now.year
            if abs(year - current_year) <= 2:  # Within 2 years
                # Return a date that's within window
                return now - datetime.timedelta(days=window_days // 2)
        except Exception:
            pass
    
    # Last resort: if string contains month name, assume recent
    date_lower = date_str.lower()
    if any(month in date_lower for month in month_names):
        return now - datetime.timedelta(days=window_days // 2)
    
    return None


def is_within_window(date_obj: Optional[datetime.datetime], window_days: int) -> bool:
    """
    Check if date is within the specified window.
    
    Args:
        date_obj: Datetime object to check
        window_days: Number of days in the window
        
    Returns:
        True if within window or date is None (permissive), False otherwise
    """
    if date_obj is None:
        return True  # Permissive: if we can't parse, include it
    
    now = datetime.datetime.now(datetime.timezone.utc)
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=datetime.timezone.utc)
    
    delta = now - date_obj
    return 0 <= delta.days <= window_days

