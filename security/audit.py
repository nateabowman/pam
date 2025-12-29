"""
Audit logging system for World P.A.M.
Logs all security-relevant operations for compliance and forensics.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from logger import get_logger
from database import Database
from async_database import AsyncDatabase


@dataclass
class AuditEvent:
    """Audit event record."""
    timestamp: str
    event_type: str
    user_id: Optional[str]
    api_key_id: Optional[str]
    action: str
    resource: str
    result: str  # "success", "failure", "denied"
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogger:
    """Audit logging system."""
    
    def __init__(self, db: Optional[Database] = None, async_db: Optional[AsyncDatabase] = None):
        """
        Initialize audit logger.
        
        Args:
            db: Synchronous database instance
            async_db: Async database instance
        """
        self.db = db
        self.async_db = async_db
        self.logger = get_logger("audit")
        self._initialize_audit_table()
    
    def _initialize_audit_table(self):
        """Initialize audit log table in database."""
        if self.db:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    api_key_id TEXT,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    result TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)")
            conn.commit()
    
    def log_event(
        self,
        event_type: str,
        action: str,
        resource: str,
        result: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (auth, api_access, data_access, config_change, etc.)
            action: Action performed (login, evaluate, read, write, delete, etc.)
            resource: Resource affected (scenario, signal, config, etc.)
            result: Result of action (success, failure, denied)
            user_id: User ID (if applicable)
            api_key_id: API key ID (if applicable)
            details: Additional details
            ip_address: Client IP address
            user_agent: Client user agent
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type,
            user_id=user_id,
            api_key_id=api_key_id,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Log to application logger
        self.logger.info(
            f"Audit: {event_type}/{action} on {resource} - {result} "
            f"(user={user_id}, key={api_key_id})"
        )
        
        # Store in database
        if self.db:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log
                (timestamp, event_type, user_id, api_key_id, action, resource, result, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp,
                event.event_type,
                event.user_id,
                event.api_key_id,
                event.action,
                event.resource,
                event.result,
                json.dumps(event.details),
                event.ip_address,
                event.user_agent
            ))
            conn.commit()
    
    async def log_event_async(
        self,
        event_type: str,
        action: str,
        resource: str,
        result: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Async version of log_event."""
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type,
            user_id=user_id,
            api_key_id=api_key_id,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.logger.info(
            f"Audit: {event_type}/{action} on {resource} - {result} "
            f"(user={user_id}, key={api_key_id})"
        )
        
        if self.async_db:
            await self.async_db._ensure_initialized()
            import aiosqlite
            async with aiosqlite.connect(self.async_db.db_path) as db:
                cursor = await db.cursor()
                await cursor.execute("""
                    INSERT INTO audit_log
                    (timestamp, event_type, user_id, api_key_id, action, resource, result, details, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.timestamp,
                    event.event_type,
                    event.user_id,
                    event.api_key_id,
                    event.action,
                    event.resource,
                    event.result,
                    json.dumps(event.details),
                    event.ip_address,
                    event.user_agent
                ))
                await db.commit()

