#!/bin/bash
# Backup script for World P.A.M. database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-backups}"
DB_PATH="${PAM_DB_PATH:-data/pam_data.db}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pam_backup_$TIMESTAMP.db"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found: $DB_PATH"
    exit 1
fi

echo "Backing up database to $BACKUP_FILE..."
cp "$DB_PATH" "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"
echo "Backup created: ${BACKUP_FILE}.gz"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/pam_backup_*.db.gz | tail -n +8 | xargs rm -f

echo "Backup complete!"

