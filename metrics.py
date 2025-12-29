"""
Metrics collection for World P.A.M.
Tracks performance metrics, request counts, and system health.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
from collections import defaultdict
import threading


@dataclass
class Metric:
    """Single metric value with timestamp."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Thread-safe metrics collector."""
    
    def __init__(self):
        self._metrics: List[Metric] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value
            self._metrics.append(Metric(
                name=name,
                value=float(value),
                tags=tags or {}
            ))
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric."""
        with self._lock:
            self._timers[name].append(duration)
            self._metrics.append(Metric(
                name=name,
                value=duration,
                tags=tags or {}
            ))
    
    def get_counter(self, name: str) -> int:
        """Get current counter value."""
        with self._lock:
            return self._counters.get(name, 0)
    
    def get_timing_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get timing statistics (mean, min, max, count)."""
        with self._lock:
            timings = self._timers.get(name, [])
            if not timings:
                return None
            
            return {
                "count": len(timings),
                "mean": sum(timings) / len(timings),
                "min": min(timings),
                "max": max(timings),
                "sum": sum(timings)
            }
    
    def get_all_metrics(self, limit: int = 1000) -> List[Metric]:
        """Get recent metrics."""
        with self._lock:
            return self._metrics[-limit:]
    
    def clear(self):
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._timers.clear()
    
    def get_summary(self) -> Dict:
        """Get summary of all metrics."""
        with self._lock:
            summary = {
                "counters": dict(self._counters),
                "timers": {}
            }
            
            for name in self._timers:
                stats = self.get_timing_stats(name)
                if stats:
                    summary["timers"][name] = stats
            
            return summary


# Global metrics collector
_global_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    return _global_metrics


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.tags = tags
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            _global_metrics.record_timing(self.name, duration, self.tags)

