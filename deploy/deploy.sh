#!/bin/bash
# Deployment script for World P.A.M.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "Deploying World P.A.M..."

# Check for required files
if [ ! -f "world_config.json" ]; then
    echo "Error: world_config.json not found"
    exit 1
fi

# Create data directory
mkdir -p data

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set defaults
export PAM_API_KEY=${PAM_API_KEY:-$(openssl rand -hex 32)}
export PAM_DB_PATH=${PAM_DB_PATH:-data/pam_data.db}
export PAM_CONFIG=${PAM_CONFIG:-world_config.json}

echo "Configuration:"
echo "  Config: $PAM_CONFIG"
echo "  DB Path: $PAM_DB_PATH"
echo "  API Key: ${PAM_API_KEY:0:8}..."

# Build Docker image
echo "Building Docker image..."
docker build -t pam:latest .

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down || true

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for health check
echo "Waiting for service to be healthy..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Service is healthy!"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    echo "Warning: Service health check timed out"
fi

echo "Deployment complete!"
echo "API available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"

