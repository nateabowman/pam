"""
Health check utilities for World P.A.M.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from metrics import get_metrics


@dataclass
class HealthCheck:
    """Single health check result."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime
    details: Optional[Dict] = None


class HealthChecker:
    """Health check manager."""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.last_check_time: Optional[datetime] = None
    
    def check_all(self) -> Dict:
        """
        Run all health checks.
        
        Returns:
            Dictionary with overall status and individual checks
        """
        self.checks.clear()
        self.last_check_time = datetime.utcnow()
        
        # Check metrics
        self._check_metrics()
        
        # Determine overall status
        unhealthy = any(c.status == "unhealthy" for c in self.checks)
        degraded = any(c.status == "degraded" for c in self.checks)
        
        if unhealthy:
            overall_status = "unhealthy"
        elif degraded:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": self.last_check_time.isoformat() + "Z",
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details
                }
                for c in self.checks
            ]
        }
    
    def _check_metrics(self):
        """Check metrics for anomalies."""
        metrics = get_metrics()
        summary = metrics.get_summary()
        
        # Check error rates
        error_count = summary["counters"].get("http_errors", 0)
        success_count = summary["counters"].get("http_success", 0)
        total_requests = error_count + success_count
        
        if total_requests > 0:
            error_rate = error_count / total_requests
            if error_rate > 0.5:
                self.checks.append(HealthCheck(
                    name="http_error_rate",
                    status="unhealthy",
                    message=f"High error rate: {error_rate:.1%}",
                    timestamp=datetime.utcnow(),
                    details={"error_rate": error_rate, "total_requests": total_requests}
                ))
            elif error_rate > 0.2:
                self.checks.append(HealthCheck(
                    name="http_error_rate",
                    status="degraded",
                    message=f"Elevated error rate: {error_rate:.1%}",
                    timestamp=datetime.utcnow(),
                    details={"error_rate": error_rate, "total_requests": total_requests}
                ))
            else:
                self.checks.append(HealthCheck(
                    name="http_error_rate",
                    status="healthy",
                    message=f"Error rate acceptable: {error_rate:.1%}",
                    timestamp=datetime.utcnow(),
                    details={"error_rate": error_rate, "total_requests": total_requests}
                ))
        else:
            self.checks.append(HealthCheck(
                name="http_error_rate",
                status="healthy",
                message="No requests yet",
                timestamp=datetime.utcnow()
            ))
        
        # Check response times
        feed_fetch_stats = summary["timers"].get("feed_fetch", {})
        if feed_fetch_stats:
            avg_time = feed_fetch_stats.get("mean", 0)
            if avg_time > 30.0:
                self.checks.append(HealthCheck(
                    name="feed_fetch_performance",
                    status="degraded",
                    message=f"Slow feed fetching: {avg_time:.1f}s average",
                    timestamp=datetime.utcnow(),
                    details=feed_fetch_stats
                ))
            else:
                self.checks.append(HealthCheck(
                    name="feed_fetch_performance",
                    status="healthy",
                    message=f"Feed fetching performance acceptable: {avg_time:.1f}s average",
                    timestamp=datetime.utcnow(),
                    details=feed_fetch_stats
                ))


# Global health checker
_global_health = HealthChecker()


def get_health() -> Dict:
    """Get health status."""
    return _global_health.check_all()

