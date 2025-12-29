"""
Caching utilities for World P.A.M.
Provides TTL-based caching for feeds, configs, and computed signals.
"""

from typing import Optional, Dict, Any, TypeVar, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import hashlib
import json

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""
    value: Any
    expires_at: datetime
    created_at: datetime


class TTLCache:
    """Thread-safe TTL cache."""
    
    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize TTL cache.
        
        Args:
            default_ttl_seconds: Default TTL in seconds (5 minutes)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            # Check expiration
            if datetime.utcnow() > entry.expires_at:
                del self._cache[key]
                return None
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds (uses default if None)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
                created_at=datetime.utcnow()
            )
    
    def delete(self, key: str):
        """Delete key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries."""
        now = datetime.utcnow()
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def size(self) -> int:
        """Get number of cache entries."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            now = datetime.utcnow()
            expired = sum(1 for entry in self._cache.values() if now > entry.expires_at)
            return {
                "total_entries": len(self._cache),
                "expired_entries": expired,
                "active_entries": len(self._cache) - expired
            }


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl_seconds: int = 300):
    """
    Decorator for caching function results.
    
    Args:
        ttl_seconds: TTL in seconds
        
    Returns:
        Decorated function
    """
    cache = TTLCache(default_ttl_seconds=ttl_seconds)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            key = cache_key(func.__name__, *args, **kwargs)
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl_seconds=ttl_seconds)
            return result
        
        wrapper.cache = cache  # Attach cache for manual control
        return wrapper
    
    return decorator


# Global caches
_feed_cache = TTLCache(default_ttl_seconds=600)  # 10 minutes for feeds
_config_cache = TTLCache(default_ttl_seconds=3600)  # 1 hour for configs
_signal_cache = TTLCache(default_ttl_seconds=300)  # 5 minutes for signals


def get_feed_cache() -> TTLCache:
    """Get global feed cache."""
    return _feed_cache


def get_config_cache() -> TTLCache:
    """Get global config cache."""
    return _config_cache


def get_signal_cache() -> TTLCache:
    """Get global signal cache."""
    return _signal_cache

