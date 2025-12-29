"""
Alert management system.
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from logger import get_logger
from streaming.event_bus import get_event_bus, Event


@dataclass
class AlertRule:
    """Alert rule definition."""
    rule_id: str
    name: str
    condition: str  # "greater_than", "less_than", "equals", "change"
    threshold: float
    scenario: Optional[str] = None
    signal: Optional[str] = None
    enabled: bool = True


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    value: float
    threshold: float
    timestamp: str
    scenario: Optional[str] = None


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.notifiers: List[Callable] = []
        self.logger = get_logger("alerts")
        self.event_bus = get_event_bus()
        
        # Subscribe to evaluation updates
        self.event_bus.subscribe("evaluation_update", self._check_evaluation_alerts)
        self.event_bus.subscribe("signal_update", self._check_signal_alerts)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.rule_id] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_id: str):
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")
    
    def add_notifier(self, notifier: Callable):
        """Add a notification handler."""
        self.notifiers.append(notifier)
    
    def _check_evaluation_alerts(self, event: Event):
        """Check alerts for evaluation updates."""
        hypothesis = event.payload.get("hypothesis")
        probability = event.payload.get("probability", 0.0)
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if rule.scenario and rule.scenario != hypothesis:
                continue
            
            if rule.condition == "greater_than" and probability > rule.threshold:
                self._trigger_alert(rule, probability, hypothesis)
            elif rule.condition == "less_than" and probability < rule.threshold:
                self._trigger_alert(rule, probability, hypothesis)
    
    def _check_signal_alerts(self, event: Event):
        """Check alerts for signal updates."""
        signal = event.payload.get("signal")
        value = event.payload.get("value", 0.0)
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if rule.signal and rule.signal != signal:
                continue
            
            if rule.condition == "greater_than" and value > rule.threshold:
                self._trigger_alert(rule, value, signal=signal)
    
    def _trigger_alert(self, rule: AlertRule, value: float, scenario: Optional[str] = None, signal: Optional[str] = None):
        """Trigger an alert."""
        import uuid
        
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            severity=self._determine_severity(value, rule.threshold),
            message=f"{rule.name}: {value:.2f} {'exceeds' if value > rule.threshold else 'below'} threshold {rule.threshold:.2f}",
            value=value,
            threshold=rule.threshold,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenario=scenario
        )
        
        self.alerts.append(alert)
        self.logger.warning(f"Alert triggered: {alert.message}")
        
        # Notify all notifiers
        for notifier in self.notifiers:
            try:
                notifier(alert)
            except Exception as e:
                self.logger.error(f"Error in notifier: {e}")
    
    def _determine_severity(self, value: float, threshold: float) -> str:
        """Determine alert severity."""
        diff = abs(value - threshold) / threshold if threshold > 0 else abs(value)
        
        if diff > 0.5:
            return "critical"
        elif diff > 0.3:
            return "high"
        elif diff > 0.1:
            return "medium"
        else:
            return "low"
    
    def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts."""
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]


# Global alert manager
_global_alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get global alert manager."""
    return _global_alert_manager

