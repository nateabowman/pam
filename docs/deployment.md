# Deployment Guide

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Python 3.11+ (for direct deployment)
- 2GB+ RAM recommended
- 10GB+ disk space for database and logs

## Quick Start (Docker)

1. **Clone and configure**:
```bash
git clone <repository-url>
cd pam
cp .env.example .env
# Edit .env and set PAM_API_KEY
```

2. **Deploy**:
```bash
./deploy/deploy.sh
```

3. **Verify**:
```bash
curl http://localhost:8000/health
```

## Manual Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Initialize Database

The database will be created automatically on first run.

### 4. Run Application

**CLI Mode**:
```bash
python pam_world.py --scenario global_war_risk
```

**API Mode**:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Production Deployment

### Using Docker Compose

1. **Configure environment**:
```bash
# .env
PAM_API_KEY=<generate-strong-key>
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
PAM_DB_PATH=/app/data/pam_data.db
```

2. **Deploy**:
```bash
docker-compose up -d
```

3. **Monitor**:
```bash
docker-compose logs -f
```

### Using Kubernetes

1. **Create ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pam-config
data:
  PAM_CONFIG: world_config.json
  LOG_LEVEL: INFO
```

2. **Create Secret**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pam-secrets
type: Opaque
stringData:
  PAM_API_KEY: <your-api-key>
```

3. **Deploy**:
```bash
kubectl apply -f k8s/
```

### Using Systemd

1. **Create service file** `/etc/systemd/system/pam.service`:
```ini
[Unit]
Description=World P.A.M. API
After=network.target

[Service]
Type=simple
User=pam
WorkingDirectory=/opt/pam
Environment="PAM_API_KEY=<your-key>"
Environment="PAM_DB_PATH=/opt/pam/data/pam_data.db"
ExecStart=/usr/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Enable and start**:
```bash
sudo systemctl enable pam
sudo systemctl start pam
```

## Reverse Proxy (Nginx)

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring

### Health Checks

```bash
# Health endpoint
curl http://localhost:8000/health

# Metrics
curl -H "X-API-Key: <key>" http://localhost:8000/api/v1/stats
```

### Logs

**Docker**:
```bash
docker-compose logs -f pam-api
```

**Systemd**:
```bash
journalctl -u pam -f
```

**File**:
```bash
tail -f data/pam.log
```

## Backup

### Automated Backup

Set up cron job:
```bash
0 2 * * * /opt/pam/deploy/backup.sh
```

### Manual Backup

```bash
./deploy/backup.sh
```

Backups are stored in `backups/` directory, compressed with gzip.

## Maintenance

### Database Cleanup

```bash
python pam_world.py --cleanup 90  # Remove data older than 90 days
```

### Update Deployment

1. **Pull latest code**:
```bash
git pull
```

2. **Rebuild**:
```bash
docker-compose build
docker-compose up -d
```

3. **Verify**:
```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Service won't start

- Check logs: `docker-compose logs`
- Verify environment variables
- Check port availability: `netstat -tulpn | grep 8000`
- Verify database permissions

### High memory usage

- Reduce `MAX_WORKERS` in environment
- Reduce cache TTL values
- Clean up old database data

### API authentication fails

- Verify `PAM_API_KEY` is set correctly
- Check API key in request header: `X-API-Key`
- Review authentication logs

### Feed fetching fails

- Check network connectivity
- Verify feed URLs are accessible
- Review rate limiting settings
- Check security whitelist

## Scaling

### Horizontal Scaling

1. Use load balancer (nginx, HAProxy)
2. Deploy multiple API instances
3. Use shared database (PostgreSQL instead of SQLite)
4. Use distributed cache (Redis)

### Vertical Scaling

1. Increase container resources
2. Adjust `MAX_WORKERS` for parallel fetching
3. Increase cache sizes
4. Optimize database queries

## Performance Tuning

- **Cache TTL**: Adjust `CACHE_TTL_FEEDS` and `CACHE_TTL_CONFIG`
- **Workers**: Adjust `MAX_WORKERS` for parallel fetching
- **Database**: Use PostgreSQL for better performance
- **Connection Pooling**: Already implemented in fetcher

## Security Hardening

See [Security Documentation](security.md) for detailed security measures.

Key points:
- Use strong API keys
- Restrict CORS origins
- Enable HTTPS
- Regular security updates
- Monitor logs for anomalies

