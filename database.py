"""
Database operations for World P.A.M.
SQLite database for storing feed items, signal values, and hypothesis evaluations.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import threading
from logger import get_logger


class Database:
    """Thread-safe SQLite database wrapper."""
    
    def __init__(self, db_path: str = "pam_data.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self.logger = get_logger("database")
        self._initialize_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _initialize_schema(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Feed items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                published TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                UNIQUE(source_name, content_hash)
            )
        """)
        
        # Signal values table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_name TEXT NOT NULL,
                value REAL NOT NULL,
                country TEXT,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                window_days INTEGER
            )
        """)
        
        # Hypothesis evaluations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hypothesis_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis_name TEXT NOT NULL,
                probability REAL NOT NULL,
                country TEXT,
                monte_carlo_mean REAL,
                monte_carlo_low REAL,
                monte_carlo_high REAL,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Source status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL UNIQUE,
                last_fetch_at TIMESTAMP,
                last_success_at TIMESTAMP,
                fetch_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feed_items_source ON feed_items(source_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feed_items_fetched ON feed_items(fetched_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_values_signal ON signal_values(signal_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_values_computed ON signal_values(computed_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_evaluations_name ON hypothesis_evaluations(hypothesis_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_evaluations_evaluated ON hypothesis_evaluations(evaluated_at)")
        
        conn.commit()
        self.logger.info("Database schema initialized")
    
    def store_feed_item(
        self,
        source_name: str,
        url: str,
        title: str,
        summary: str,
        published: Optional[str] = None
    ) -> int:
        """
        Store a feed item.
        
        Args:
            source_name: Name of the source
            url: Feed URL
            title: Item title
            summary: Item summary
            published: Publication date string
            
        Returns:
            Inserted row ID
        """
        import hashlib
        content_hash = hashlib.md5(f"{title}{summary}".encode()).hexdigest()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO feed_items
                (source_name, url, title, summary, published, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (source_name, url, title, summary, published, content_hash))
            
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Duplicate, return existing ID
            cursor.execute("""
                SELECT id FROM feed_items
                WHERE source_name = ? AND content_hash = ?
            """, (source_name, content_hash))
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def store_signal_value(
        self,
        signal_name: str,
        value: float,
        country: Optional[str] = None,
        window_days: int = 7
    ):
        """Store a computed signal value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO signal_values
            (signal_name, value, country, window_days)
            VALUES (?, ?, ?, ?)
        """, (signal_name, value, country, window_days))
        
        conn.commit()
    
    def store_hypothesis_evaluation(
        self,
        hypothesis_name: str,
        probability: float,
        country: Optional[str] = None,
        monte_carlo_mean: Optional[float] = None,
        monte_carlo_low: Optional[float] = None,
        monte_carlo_high: Optional[float] = None
    ):
        """Store a hypothesis evaluation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO hypothesis_evaluations
            (hypothesis_name, probability, country, monte_carlo_mean, monte_carlo_low, monte_carlo_high)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (hypothesis_name, probability, country, monte_carlo_mean, monte_carlo_low, monte_carlo_high))
        
        conn.commit()
    
    def update_source_status(
        self,
        source_name: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Update source fetch status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        # Get existing status
        cursor.execute("SELECT * FROM source_status WHERE source_name = ?", (source_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            if success:
                cursor.execute("""
                    UPDATE source_status
                    SET last_fetch_at = ?, last_success_at = ?, fetch_count = fetch_count + 1,
                        last_error = NULL
                    WHERE source_name = ?
                """, (now, now, source_name))
            else:
                cursor.execute("""
                    UPDATE source_status
                    SET last_fetch_at = ?, error_count = error_count + 1, last_error = ?,
                        fetch_count = fetch_count + 1
                    WHERE source_name = ?
                """, (now, error, source_name))
        else:
            # Insert new
            if success:
                cursor.execute("""
                    INSERT INTO source_status
                    (source_name, last_fetch_at, last_success_at, fetch_count)
                    VALUES (?, ?, ?, 1)
                """, (source_name, now, now))
            else:
                cursor.execute("""
                    INSERT INTO source_status
                    (source_name, last_fetch_at, error_count, last_error, fetch_count)
                    VALUES (?, ?, 1, ?, 1)
                """, (source_name, now, error))
        
        conn.commit()
    
    def get_feed_items(
        self,
        source_name: Optional[str] = None,
        days: int = 7,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get feed items within time window."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        if source_name:
            cursor.execute("""
                SELECT * FROM feed_items
                WHERE source_name = ? AND fetched_at >= ?
                ORDER BY fetched_at DESC
                LIMIT ?
            """, (source_name, cutoff, limit))
        else:
            cursor.execute("""
                SELECT * FROM feed_items
                WHERE fetched_at >= ?
                ORDER BY fetched_at DESC
                LIMIT ?
            """, (cutoff, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_signal_history(
        self,
        signal_name: str,
        days: int = 30,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get signal value history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        if country:
            cursor.execute("""
                SELECT * FROM signal_values
                WHERE signal_name = ? AND country = ? AND computed_at >= ?
                ORDER BY computed_at DESC
            """, (signal_name, country, cutoff))
        else:
            cursor.execute("""
                SELECT * FROM signal_values
                WHERE signal_name = ? AND computed_at >= ?
                ORDER BY computed_at DESC
            """, (signal_name, cutoff))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_hypothesis_history(
        self,
        hypothesis_name: str,
        days: int = 30,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get hypothesis evaluation history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        if country:
            cursor.execute("""
                SELECT * FROM hypothesis_evaluations
                WHERE hypothesis_name = ? AND country = ? AND evaluated_at >= ?
                ORDER BY evaluated_at DESC
            """, (hypothesis_name, country, cutoff))
        else:
            cursor.execute("""
                SELECT * FROM hypothesis_evaluations
                WHERE hypothesis_name = ? AND evaluated_at >= ?
                ORDER BY evaluated_at DESC
            """, (hypothesis_name, cutoff))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def export_to_json(self, output_path: str, days: int = 30):
        """Export data to JSON file."""
        data = {
            "feed_items": self.get_feed_items(days=days),
            "source_status": self._get_all_source_status(),
            "exported_at": datetime.utcnow().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Exported data to {output_path}")
    
    def _get_all_source_status(self) -> List[Dict[str, Any]]:
        """Get all source status records."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM source_status")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def cleanup_old_data(self, days: int = 90):
        """Remove data older than specified days."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        cursor.execute("DELETE FROM feed_items WHERE fetched_at < ?", (cutoff,))
        feed_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM signal_values WHERE computed_at < ?", (cutoff,))
        signal_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM hypothesis_evaluations WHERE evaluated_at < ?", (cutoff,))
        eval_deleted = cursor.rowcount
        
        conn.commit()
        
        self.logger.info(f"Cleaned up old data: {feed_deleted} feed items, {signal_deleted} signals, {eval_deleted} evaluations")
        
        return {
            "feed_items": feed_deleted,
            "signals": signal_deleted,
            "evaluations": eval_deleted
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')

