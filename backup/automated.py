"""
Automated backup system.
"""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from logger import get_logger
from jobs.scheduler import get_scheduler


class BackupManager:
    """Manages automated backups."""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.logger = get_logger("backup")
    
    async def backup_database(self, db_path: str) -> str:
        """
        Backup database file.
        
        Args:
            db_path: Path to database file
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"pam_backup_{timestamp}.db"
        
        try:
            shutil.copy2(db_path, backup_path)
            self.logger.info(f"Database backed up to {backup_path}")
            return str(backup_path)
        except Exception as e:
            self.logger.error(f"Error backing up database: {e}")
            raise
    
    async def schedule_backups(self, db_path: str, interval_hours: int = 24):
        """Schedule automatic backups."""
        scheduler = get_scheduler()
        
        async def backup_job():
            await self.backup_database(db_path)
            # Clean old backups (keep last 7)
            await self.cleanup_old_backups(keep_count=7)
        
        await scheduler.schedule_periodic(
            "database_backup",
            backup_job,
            interval_seconds=interval_hours * 3600,
            start_immediately=False
        )
    
    async def cleanup_old_backups(self, keep_count: int = 7):
        """Remove old backups, keeping only the most recent ones."""
        backups = sorted(self.backup_dir.glob("pam_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if len(backups) > keep_count:
            for backup in backups[keep_count:]:
                backup.unlink()
                self.logger.info(f"Deleted old backup: {backup}")

