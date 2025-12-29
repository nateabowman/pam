"""
PostgreSQL adapter for World P.A.M.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncpg
from logger import get_logger


class PostgreSQLDatabase:
    """PostgreSQL database adapter."""
    
    def __init__(self, connection_string: str):
        """
        Initialize PostgreSQL connection.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        self.logger = get_logger("postgres")
    
    async def initialize(self, pool_size: int = 10):
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=pool_size
        )
        await self._initialize_schema()
        self.logger.info("PostgreSQL database initialized")
    
    async def _initialize_schema(self):
        """Initialize database schema."""
        async with self.pool.acquire() as conn:
            # Similar schema to SQLite version
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS feed_items (
                    id SERIAL PRIMARY KEY,
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
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_items_source ON feed_items(source_name)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_items_fetched ON feed_items(fetched_at)
            """)
            
            # Add other tables similarly...
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

