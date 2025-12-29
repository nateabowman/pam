"""
Webhook subscription management.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
from logger import get_logger


@dataclass
class WebhookSubscription:
    """Webhook subscription definition."""
    subscription_id: str
    url: str
    event_types: List[str]
    secret: str
    active: bool = True
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat() + "Z"


class WebhookManager:
    """Manages webhook subscriptions."""
    
    def __init__(self):
        self.subscriptions: Dict[str, WebhookSubscription] = {}
        self.logger = get_logger("webhooks")
    
    def create_subscription(
        self,
        url: str,
        event_types: List[str],
        secret: Optional[str] = None
    ) -> WebhookSubscription:
        """
        Create a new webhook subscription.
        
        Args:
            url: Webhook URL
            event_types: List of event types to subscribe to
            secret: Optional secret for webhook signing
            
        Returns:
            WebhookSubscription
        """
        import secrets
        subscription_id = str(uuid.uuid4())
        secret = secret or secrets.token_urlsafe(32)
        
        subscription = WebhookSubscription(
            subscription_id=subscription_id,
            url=url,
            event_types=event_types,
            secret=secret
        )
        
        self.subscriptions[subscription_id] = subscription
        self.logger.info(f"Created webhook subscription: {subscription_id}")
        
        return subscription
    
    def get_subscriptions_for_event(self, event_type: str) -> List[WebhookSubscription]:
        """Get all active subscriptions for an event type."""
        return [
            sub for sub in self.subscriptions.values()
            if sub.active and event_type in sub.event_types
        ]
    
    async def deliver_webhook(self, subscription: WebhookSubscription, event: Dict):
        """Deliver webhook event."""
        import aiohttp
        import hmac
        import hashlib
        import json
        
        payload = json.dumps(event)
        signature = hmac.new(
            subscription.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    subscription.url,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        self.logger.info(f"Delivered webhook to {subscription.url}")
                    else:
                        self.logger.warning(f"Webhook delivery failed: {resp.status}")
        except Exception as e:
            self.logger.error(f"Error delivering webhook: {e}")


# Global webhook manager
_global_webhook_manager = WebhookManager()


def get_webhook_manager() -> WebhookManager:
    """Get global webhook manager."""
    return _global_webhook_manager

