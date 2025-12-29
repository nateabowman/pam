"""
Task scheduler for periodic jobs.
"""

import asyncio
from typing import Dict, Callable, Optional
from datetime import datetime, timedelta
from logger import get_logger


class TaskScheduler:
    """Simple task scheduler."""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.jobs: Dict[str, Dict] = {}
        self.logger = get_logger("scheduler")
    
    async def schedule_periodic(
        self,
        job_id: str,
        func: Callable,
        interval_seconds: int,
        start_immediately: bool = False
    ):
        """
        Schedule a periodic task.
        
        Args:
            job_id: Unique job identifier
            func: Async function to execute
            interval_seconds: Interval between executions
            start_immediately: Whether to run immediately
        """
        if job_id in self.tasks:
            self.logger.warning(f"Job {job_id} already scheduled, cancelling previous")
            self.tasks[job_id].cancel()
        
        self.jobs[job_id] = {
            "func": func,
            "interval": interval_seconds,
            "last_run": None
        }
        
        async def run_periodic():
            if not start_immediately:
                await asyncio.sleep(interval_seconds)
            
            while True:
                try:
                    self.logger.info(f"Running scheduled job: {job_id}")
                    self.jobs[job_id]["last_run"] = datetime.utcnow()
                    await func()
                except Exception as e:
                    self.logger.error(f"Error in scheduled job {job_id}: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        self.tasks[job_id] = asyncio.create_task(run_periodic())
        self.logger.info(f"Scheduled job: {job_id} (interval: {interval_seconds}s)")
    
    def cancel_job(self, job_id: str):
        """Cancel a scheduled job."""
        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            del self.tasks[job_id]
            del self.jobs[job_id]
            self.logger.info(f"Cancelled job: {job_id}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a job."""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return {
            "job_id": job_id,
            "interval": job["interval"],
            "last_run": job["last_run"].isoformat() if job["last_run"] else None,
            "running": job_id in self.tasks and not self.tasks[job_id].done()
        }


# Global scheduler
_global_scheduler = TaskScheduler()


def get_scheduler() -> TaskScheduler:
    """Get global scheduler."""
    return _global_scheduler

