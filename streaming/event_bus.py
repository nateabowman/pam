"""
Event bus for event-driven architecture.
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
from logger import get_logger


@dataclass
class Event:
    """Event data structure."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: str
    source: Optional[str] = None


class EventBus:
    """Simple in-memory event bus."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.logger = get_logger("event_bus")
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Handler function
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        self.logger.debug(f"Subscribed to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)
    
    async def publish(self, event: Event):
        """
        Publish an event.
        
        Args:
            event: Event to publish
        """
        handlers = self.subscribers.get(event.event_type, [])
        self.logger.debug(f"Publishing {event.event_type} to {len(handlers)} handlers")
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event.event_type}: {e}")
    
    def publish_sync(self, event: Event):
        """Synchronous version of publish."""
        handlers = self.subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event.event_type}: {e}")


# Global event bus
_global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get global event bus."""
    return _global_event_bus

