"""
Slack notification handler.
"""

import aiohttp
from typing import Dict, Any
import os
from logger import get_logger
from alerts.alert_manager import Alert


class SlackNotifier:
    """Slack webhook notification handler."""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.logger = get_logger("slack_notifier")
    
    async def send_alert(self, alert: Alert):
        """Send alert to Slack."""
        if not self.webhook_url:
            self.logger.warning("Slack webhook URL not configured")
            return
        
        payload = {
            "text": f"P.A.M. Alert: {alert.severity.upper()}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{alert.message}*\nValue: {alert.value:.2f}\nThreshold: {alert.threshold:.2f}"
                    }
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        self.logger.info(f"Sent Slack alert: {alert.message}")
                    else:
                        self.logger.error(f"Failed to send Slack alert: {resp.status}")
        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")

