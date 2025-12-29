"""
Security tests for World P.A.M.
"""

import pytest
from security import (
    validate_url,
    fetch_url_secure,
    check_rate_limit,
    get_allowed_netlocs_from_config
)


def test_validate_url_allowed_schemes():
    """Test URL validation with allowed schemes."""
    assert validate_url("https://example.com") is True
    assert validate_url("http://example.com") is True
    assert validate_url("ftp://example.com") is False
    assert validate_url("file:///etc/passwd") is False


def test_validate_url_localhost():
    """Test URL validation blocks localhost."""
    assert validate_url("http://localhost") is False
    assert validate_url("http://127.0.0.1") is False
    assert validate_url("http://0.0.0.0") is False


def test_validate_url_private_ips():
    """Test URL validation blocks private IP ranges."""
    assert validate_url("http://10.0.0.1") is False
    assert validate_url("http://192.168.1.1") is False
    assert validate_url("http://172.16.0.1") is False


def test_validate_url_whitelist():
    """Test URL validation with whitelist."""
    allowed = {"example.com", "test.com"}
    assert validate_url("http://example.com", allowed_netlocs=allowed) is True
    assert validate_url("http://evil.com", allowed_netlocs=allowed) is False
    assert validate_url("http://www.example.com", allowed_netlocs=allowed) is True


def test_rate_limiting():
    """Test rate limiting."""
    url = "https://example.com"
    
    # Clear rate limit
    from security import _rate_limit_store
    _rate_limit_store.clear()
    
    # Should allow requests up to limit
    for _ in range(10):
        assert check_rate_limit(url) is True
    
    # Should block after limit
    assert check_rate_limit(url) is False


def test_get_allowed_netlocs():
    """Test extracting allowed netlocs from config."""
    sources = [
        {"url": "https://example.com/feed"},
        {"url": "http://test.com/rss"},
        {"url": "https://www.news.com/feed"}
    ]
    
    netlocs = get_allowed_netlocs_from_config(sources)
    assert "example.com" in netlocs
    assert "test.com" in netlocs
    assert "news.com" in netlocs  # www prefix removed
    assert "www.news.com" in netlocs  # Also includes with www

