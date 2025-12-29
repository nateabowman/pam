"""
Background workers for async processing.
"""

import asyncio
from typing import Callable, Any, Optional
from logger import get_logger
from streaming.event_bus import get_event_bus, Event


class WorkerPool:
    """Pool of background workers."""
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize worker pool.
        
        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.logger = get_logger("workers")
        self.event_bus = get_event_bus()
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function in the worker pool.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
        """
        async with self.semaphore:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in worker: {e}")
                raise
    
    async def execute_batch(self, tasks: List[Callable]) -> List[Any]:
        """
        Execute multiple tasks concurrently.
        
        Args:
            tasks: List of async functions
            
        Returns:
            List of results
        """
        return await asyncio.gather(*[self.execute(task) for task in tasks])


# Global worker pool
_global_worker_pool = WorkerPool()


def get_worker_pool() -> WorkerPool:
    """Get global worker pool."""
    return _global_worker_pool

