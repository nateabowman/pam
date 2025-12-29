"""
Redis cache implementation for distributed caching.
"""

from typing import Optional, Any
import json
import redis.asyncio as redis
from logger import get_logger


class RedisCache:
    """Redis-based distributed cache."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        self.logger = get_logger("redis_cache")
    
    async def connect(self):
        """Connect to Redis."""
        self.client = await redis.from_url(self.redis_url)
        self.logger.info("Connected to Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.client:
            await self.connect()
        
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            self.logger.error(f"Error getting from Redis: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in cache with TTL."""
        if not self.client:
            await self.connect()
        
        try:
            await self.client.setex(
                key,
                ttl_seconds,
                json.dumps(value)
            )
        except Exception as e:
            self.logger.error(f"Error setting in Redis: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        if not self.client:
            await self.connect()
        
        try:
            await self.client.delete(key)
        except Exception as e:
            self.logger.error(f"Error deleting from Redis: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()

