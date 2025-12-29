"""
Async database operations for World P.A.M.
Uses aiosqlite for async SQLite operations.
"""

import aiosqlite
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from logger import get_logger


class AsyncDatabase:
    """Async SQLite database wrapper."""
    
    def __init__(self, db_path: str = "pam_data.db"):
        """
        Initialize async database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = get_logger("async_database")
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database schema is initialized."""
        if not self._initialized:
            async with aiosqlite.connect(self.db_path) as db:
                await self._initialize_schema(db)
            self._initialized = True
    
    async def _initialize_schema(self, db: aiosqlite.Connection):
        """Initialize database schema."""
        cursor = await db.cursor()
        
        # Feed items table
        await cursor.execute("""
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
        await cursor.execute("""
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
        await cursor.execute("""
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
        await cursor.execute("""
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
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_feed_items_source ON feed_items(source_name)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_feed_items_fetched ON feed_items(fetched_at)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_values_signal ON signal_values(signal_name)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_values_computed ON signal_values(computed_at)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_evaluations_name ON hypothesis_evaluations(hypothesis_name)")
        await cursor.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_evaluations_evaluated ON hypothesis_evaluations(evaluated_at)")
        
        await db.commit()
        self.logger.info("Async database schema initialized")
    
    async def store_feed_item(
        self,
        source_name: str,
        url: str,
        title: str,
        summary: str,
        published: Optional[str] = None
    ) -> int:
        """Store a feed item."""
        await self._ensure_initialized()
        
        import hashlib
        content_hash = hashlib.md5(f"{title}{summary}".encode()).hexdigest()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            try:
                await cursor.execute("""
                    INSERT OR IGNORE INTO feed_items
                    (source_name, url, title, summary, published, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (source_name, url, title, summary, published, content_hash))
                
                await db.commit()
                return cursor.lastrowid
            except Exception:
                # If insert failed, try to get existing ID
                await cursor.execute("""
                    SELECT id FROM feed_items
                    WHERE source_name = ? AND content_hash = ?
                """, (source_name, content_hash))
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def store_signal_value(
        self,
        signal_name: str,
        value: float,
        country: Optional[str] = None,
        window_days: int = 7
    ):
        """Store a computed signal value."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute("""
                INSERT INTO signal_values
                (signal_name, value, country, window_days)
                VALUES (?, ?, ?, ?)
            """, (signal_name, value, country, window_days))
            await db.commit()
    
    async def store_hypothesis_evaluation(
        self,
        hypothesis_name: str,
        probability: float,
        country: Optional[str] = None,
        monte_carlo_mean: Optional[float] = None,
        monte_carlo_low: Optional[float] = None,
        monte_carlo_high: Optional[float] = None
    ):
        """Store a hypothesis evaluation."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            await cursor.execute("""
                INSERT INTO hypothesis_evaluations
                (hypothesis_name, probability, country, monte_carlo_mean, monte_carlo_low, monte_carlo_high)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (hypothesis_name, probability, country, monte_carlo_mean, monte_carlo_low, monte_carlo_high))
            await db.commit()
    
    async def update_source_status(
        self,
        source_name: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Update source fetch status."""
        await self._ensure_initialized()
        
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.cursor()
            
            # Check if exists
            await cursor.execute("SELECT * FROM source_status WHERE source_name = ?", (source_name,))
            existing = await cursor.fetchone()
            
            if existing:
                if success:
                    await cursor.execute("""
                        UPDATE source_status
                        SET last_fetch_at = ?, last_success_at = ?, fetch_count = fetch_count + 1,
                            last_error = NULL
                        WHERE source_name = ?
                    """, (now, now, source_name))
                else:
                    await cursor.execute("""
                        UPDATE source_status
                        SET last_fetch_at = ?, error_count = error_count + 1, last_error = ?,
                            fetch_count = fetch_count + 1
                        WHERE source_name = ?
                    """, (now, error, source_name))
            else:
                if success:
                    await cursor.execute("""
                        INSERT INTO source_status
                        (source_name, last_fetch_at, last_success_at, fetch_count)
                        VALUES (?, ?, ?, 1)
                    """, (source_name, now, now))
                else:
                    await cursor.execute("""
                        INSERT INTO source_status
                        (source_name, last_fetch_at, error_count, last_error, fetch_count)
                        VALUES (?, ?, 1, ?, 1)
                    """, (source_name, now, error))
            
            await db.commit()
    
    async def get_hypothesis_history(
        self,
        hypothesis_name: str,
        days: int = 30,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get hypothesis evaluation history."""
        await self._ensure_initialized()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.cursor()
            
            if country:
                await cursor.execute("""
                    SELECT * FROM hypothesis_evaluations
                    WHERE hypothesis_name = ? AND country = ? AND evaluated_at >= ?
                    ORDER BY evaluated_at DESC
                """, (hypothesis_name, country, cutoff))
            else:
                await cursor.execute("""
                    SELECT * FROM hypothesis_evaluations
                    WHERE hypothesis_name = ? AND evaluated_at >= ?
                    ORDER BY evaluated_at DESC
                """, (hypothesis_name, cutoff))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

