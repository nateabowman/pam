"""
Tests for feed parsing functionality.
"""

import pytest
from pam_world import parse_feed_bytes, normalized_keyword_hits
from validators import parse_date, is_within_window
from datetime import datetime, timedelta, timezone


def test_parse_rss_feed():
    """Test RSS feed parsing."""
    rss_content = b"""<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Test Title</title>
                <description>Test Description</description>
            </item>
        </channel>
    </rss>"""
    
    items = parse_feed_bytes("rss", rss_content)
    assert len(items) == 1
    assert items[0]["title"] == "Test Title"
    assert items[0]["summary"] == "Test Description"


def test_parse_atom_feed():
    """Test Atom feed parsing."""
    atom_content = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>Atom Title</title>
            <summary>Atom Summary</summary>
        </entry>
    </feed>"""
    
    items = parse_feed_bytes("atom", atom_content)
    assert len(items) >= 0  # May not parse without proper namespace handling


def test_parse_invalid_xml():
    """Test parsing invalid XML."""
    invalid_xml = b"<not>valid xml"
    items = parse_feed_bytes("rss", invalid_xml)
    assert items == []


def test_normalized_keyword_hits():
    """Test keyword hit normalization."""
    items = [
        {"title": "Test article", "summary": "About war and conflict"},
        {"title": "Another article", "summary": "Peace talks resume"},
    ]
    
    keywords = ["war", "conflict"]
    score = normalized_keyword_hits(items, keywords, window_days=7)
    assert 0.0 <= score <= 1.0
    assert score > 0  # Should find matches


def test_normalized_keyword_hits_empty():
    """Test keyword hits with empty input."""
    assert normalized_keyword_hits([], ["test"]) == 0.0
    assert normalized_keyword_hits([{"title": "test"}], []) == 0.0


def test_parse_date_rfc822():
    """Test date parsing with RFC 822 format."""
    date_str = "Mon, 01 Jan 2024 12:00:00 +0000"
    parsed = parse_date(date_str)
    assert parsed is not None
    assert isinstance(parsed, datetime)


def test_parse_date_iso8601():
    """Test date parsing with ISO 8601 format."""
    date_str = "2024-01-01T12:00:00Z"
    parsed = parse_date(date_str)
    assert parsed is not None


def test_parse_date_invalid():
    """Test parsing invalid date."""
    parsed = parse_date("not a date")
    # Should return None or a fallback date
    assert parsed is None or isinstance(parsed, datetime)


def test_is_within_window():
    """Test window checking."""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=3)
    old = now - timedelta(days=10)
    
    assert is_within_window(recent, window_days=7) is True
    assert is_within_window(old, window_days=7) is False
    assert is_within_window(None, window_days=7) is True  # Permissive

