"""
Distributed locking mechanism.
"""

import asyncio
import time
from typing import Optional
from logger import get_logger


class DistributedLock:
    """Simple distributed lock (can be enhanced with Redis)."""
    
    def __init__(self, lock_id: str, timeout: float = 30.0):
        """
        Initialize distributed lock.
        
        Args:
            lock_id: Unique lock identifier
            timeout: Lock timeout in seconds
        """
        self.lock_id = lock_id
        self.timeout = timeout
        self.acquired = False
        self.acquired_at: Optional[float] = None
        self.logger = get_logger("distributed_lock")
    
    async def acquire(self) -> bool:
        """
        Acquire lock.
        
        Returns:
            True if acquired
        """
        # Simple implementation - in production, use Redis or similar
        if not self.acquired:
            self.acquired = True
            self.acquired_at = time.time()
            self.logger.debug(f"Acquired lock: {self.lock_id}")
            return True
        return False
    
    async def release(self):
        """Release lock."""
        if self.acquired:
            self.acquired = False
            self.acquired_at = None
            self.logger.debug(f"Released lock: {self.lock_id}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()

