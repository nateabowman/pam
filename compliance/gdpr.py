"""
GDPR compliance utilities for World P.A.M.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from logger import get_logger
from database import Database
from async_database import AsyncDatabase


class GDPRCompliance:
    """GDPR compliance manager."""
    
    def __init__(self, db: Optional[Database] = None, async_db: Optional[AsyncDatabase] = None):
        """
        Initialize GDPR compliance manager.
        
        Args:
            db: Synchronous database
            async_db: Async database
        """
        self.db = db
        self.async_db = async_db
        self.logger = get_logger("gdpr")
    
    def anonymize_user_data(self, user_id: str) -> bool:
        """
        Anonymize all data associated with a user.
        
        Args:
            user_id: User ID to anonymize
            
        Returns:
            True if successful
        """
        if not self.db:
            return False
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Anonymize audit logs
            cursor.execute("""
                UPDATE audit_log
                SET user_id = NULL, api_key_id = NULL, ip_address = NULL, user_agent = NULL
                WHERE user_id = ? OR api_key_id = ?
            """, (user_id, user_id))
            
            conn.commit()
            self.logger.info(f"Anonymized data for user: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error anonymizing user data: {e}")
            return False
    
    async def anonymize_user_data_async(self, user_id: str) -> bool:
        """Async version of anonymize_user_data."""
        if not self.async_db:
            return False
        
        try:
            await self.async_db._ensure_initialized()
            import aiosqlite
            async with aiosqlite.connect(self.async_db.db_path) as db:
                cursor = await db.cursor()
                await cursor.execute("""
                    UPDATE audit_log
                    SET user_id = NULL, api_key_id = NULL, ip_address = NULL, user_agent = NULL
                    WHERE user_id = ? OR api_key_id = ?
                """, (user_id, user_id))
                await db.commit()
            
            self.logger.info(f"Anonymized data for user: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error anonymizing user data: {e}")
            return False
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all data associated with a user (GDPR right to data portability).
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user data
        """
        if not self.db:
            return {}
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Get audit logs
            cursor.execute("SELECT * FROM audit_log WHERE user_id = ? OR api_key_id = ?", (user_id, user_id))
            audit_logs = [dict(row) for row in cursor.fetchall()]
            
            return {
                "user_id": user_id,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "audit_logs": audit_logs
            }
        except Exception as e:
            self.logger.error(f"Error exporting user data: {e}")
            return {}
    
    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all data associated with a user (GDPR right to be forgotten).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        if not self.db:
            return False
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Delete audit logs
            cursor.execute("DELETE FROM audit_log WHERE user_id = ? OR api_key_id = ?", (user_id, user_id))
            
            conn.commit()
            self.logger.info(f"Deleted data for user: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting user data: {e}")
            return False
    
    def apply_data_retention_policy(self, days: int = 90) -> int:
        """
        Apply data retention policy (delete data older than specified days).
        
        Args:
            days: Number of days to retain
            
        Returns:
            Number of records deleted
        """
        if not self.db:
            return 0
        
        try:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Delete old audit logs
            cursor.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            deleted = cursor.rowcount
            
            conn.commit()
            self.logger.info(f"Applied retention policy: deleted {deleted} records older than {days} days")
            return deleted
        except Exception as e:
            self.logger.error(f"Error applying retention policy: {e}")
            return 0

