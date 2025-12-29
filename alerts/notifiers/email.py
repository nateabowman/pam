"""
Email notification handler.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import os
from logger import get_logger
from alerts.alert_manager import Alert


class EmailNotifier:
    """Email notification handler."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_FROM", "pam@example.com")
        self.logger = get_logger("email_notifier")
    
    async def send_alert(self, alert: Alert, recipients: list[str]):
        """
        Send alert via email.
        
        Args:
            alert: Alert to send
            recipients: List of email addresses
        """
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"P.A.M. Alert: {alert.severity.upper()} - {alert.message}"
            
            body = f"""
            Alert: {alert.message}
            Severity: {alert.severity}
            Value: {alert.value:.2f}
            Threshold: {alert.threshold:.2f}
            Time: {alert.timestamp}
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email (simplified - use async SMTP in production)
            # For now, just log
            self.logger.info(f"Would send email alert to {recipients}: {alert.message}")
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")

