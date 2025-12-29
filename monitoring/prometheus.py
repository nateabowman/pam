"""
Prometheus metrics exporter for World P.A.M.
"""

from prometheus_client import Counter, Histogram, Gauge
from logger import get_logger


# Prometheus metrics
http_requests_total = Counter(
    'pam_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'pam_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

signal_computations = Counter(
    'pam_signal_computations_total',
    'Total signal computations',
    ['signal_name']
)

hypothesis_evaluations = Counter(
    'pam_hypothesis_evaluations_total',
    'Total hypothesis evaluations',
    ['hypothesis_name']
)

active_connections = Gauge(
    'pam_active_connections',
    'Active WebSocket connections'
)


class PrometheusExporter:
    """Prometheus metrics exporter."""
    
    def __init__(self):
        self.logger = get_logger("prometheus")
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics."""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_signal_computation(self, signal_name: str):
        """Record signal computation."""
        signal_computations.labels(signal_name=signal_name).inc()
    
    def record_hypothesis_evaluation(self, hypothesis_name: str):
        """Record hypothesis evaluation."""
        hypothesis_evaluations.labels(hypothesis_name=hypothesis_name).inc()
    
    def update_connections(self, count: int):
        """Update active connections count."""
        active_connections.set(count)

