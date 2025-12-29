"""
Tests for database functionality.
"""

import pytest
import os
import tempfile
from database import Database
from datetime import datetime, timedelta


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    yield db
    db.close()
    os.unlink(path)


def test_database_initialization(temp_db):
    """Test database initialization."""
    # Should create tables
    conn = temp_db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "feed_items" in tables
    assert "signal_values" in tables
    assert "hypothesis_evaluations" in tables
    assert "source_status" in tables


def test_store_feed_item(temp_db):
    """Test storing feed items."""
    item_id = temp_db.store_feed_item(
        source_name="test_source",
        url="https://example.com",
        title="Test Title",
        summary="Test Summary",
        published="2024-01-01"
    )
    assert item_id > 0


def test_store_feed_item_duplicate(temp_db):
    """Test storing duplicate feed items."""
    item_id1 = temp_db.store_feed_item(
        source_name="test_source",
        url="https://example.com",
        title="Test Title",
        summary="Test Summary"
    )
    item_id2 = temp_db.store_feed_item(
        source_name="test_source",
        url="https://example.com",
        title="Test Title",
        summary="Test Summary"
    )
    # Should return same ID for duplicate
    assert item_id1 == item_id2


def test_store_signal_value(temp_db):
    """Test storing signal values."""
    temp_db.store_signal_value("test_signal", 0.75, country="TestCountry", window_days=7)
    
    history = temp_db.get_signal_history("test_signal", days=1)
    assert len(history) == 1
    assert history[0]["value"] == 0.75


def test_store_hypothesis_evaluation(temp_db):
    """Test storing hypothesis evaluations."""
    temp_db.store_hypothesis_evaluation(
        hypothesis_name="test_hypothesis",
        probability=0.25,
        country="TestCountry",
        monte_carlo_mean=0.26,
        monte_carlo_low=0.20,
        monte_carlo_high=0.30
    )
    
    history = temp_db.get_hypothesis_history("test_hypothesis", days=1)
    assert len(history) == 1
    assert history[0]["probability"] == 0.25


def test_get_feed_items(temp_db):
    """Test retrieving feed items."""
    # Store some items
    for i in range(5):
        temp_db.store_feed_item(
            source_name="test_source",
            url=f"https://example.com/{i}",
            title=f"Title {i}",
            summary=f"Summary {i}"
        )
    
    items = temp_db.get_feed_items(source_name="test_source", days=1)
    assert len(items) == 5


def test_cleanup_old_data(temp_db):
    """Test cleaning up old data."""
    # Store old item (simulated)
    temp_db.store_feed_item(
        source_name="test_source",
        url="https://example.com/old",
        title="Old Title",
        summary="Old Summary"
    )
    
    # Cleanup data older than 0 days (everything)
    result = temp_db.cleanup_old_data(days=0)
    assert result["feed_items"] > 0

