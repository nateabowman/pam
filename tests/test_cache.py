"""
Tests for caching functionality.
"""

import pytest
import time
from cache import TTLCache, cache_key, cached


def test_ttl_cache_set_get():
    """Test basic cache set/get."""
    cache = TTLCache(default_ttl_seconds=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_ttl_cache_expiration():
    """Test cache expiration."""
    cache = TTLCache(default_ttl_seconds=1)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_ttl_cache_custom_ttl():
    """Test cache with custom TTL."""
    cache = TTLCache(default_ttl_seconds=60)
    cache.set("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_ttl_cache_delete():
    """Test cache deletion."""
    cache = TTLCache()
    cache.set("key1", "value1")
    cache.delete("key1")
    assert cache.get("key1") is None


def test_ttl_cache_clear():
    """Test cache clearing."""
    cache = TTLCache()
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_cache_key_generation():
    """Test cache key generation."""
    key1 = cache_key("func", "arg1", kwarg1="value1")
    key2 = cache_key("func", "arg1", kwarg1="value1")
    key3 = cache_key("func", "arg2", kwarg1="value1")
    
    assert key1 == key2  # Same args = same key
    assert key1 != key3  # Different args = different key


def test_cached_decorator():
    """Test @cached decorator."""
    call_count = [0]
    
    @cached(ttl_seconds=60)
    def test_func(x):
        call_count[0] += 1
        return x * 2
    
    result1 = test_func(5)
    result2 = test_func(5)
    
    assert result1 == 10
    assert result2 == 10
    assert call_count[0] == 1  # Function called only once due to caching

