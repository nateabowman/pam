# World P.A.M. - Predictive Analytic Machine

**World P.A.M.** is a predictive analytic machine for evaluating geopolitical, environmental, and social risk hypotheses based on live public RSS/Atom feeds from news sources and international organizations.

## Features

- **Live Feed Analysis**: Fetches and analyzes RSS/Atom feeds from Reuters, BBC, UN, NATO, IAEA, and more
- **Signal Extraction**: Keyword-based signal extraction with normalization
- **Hypothesis Evaluation**: Logistic model-based probability evaluation for multiple scenarios
- **Historical Tracking**: SQLite database for storing feed items, signals, and evaluations over time
- **REST API**: FastAPI-based REST API with OpenAPI documentation
- **Web Dashboard**: Simple web interface for viewing results
- **Security Hardened**: URL validation, rate limiting, XML protection, input validation
- **Performance Optimized**: Parallel feed fetching, TTL-based caching, connection pooling
- **Production Ready**: Docker support, health checks, logging, metrics, monitoring

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) Docker and Docker Compose

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pam
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run with default configuration:
```bash
python pam_world.py --list
python pam_world.py --scenario global_war_risk --simulate 5000 --explain
```

### Docker Deployment

1. Copy environment variables:
```bash
cp .env.example .env
# Edit .env and set PAM_API_KEY
```

2. Deploy:
```bash
./deploy/deploy.sh
```

3. Access API:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Dashboard: http://localhost:8000/dashboard

## Usage

### Command Line

```bash
# List available scenarios
python pam_world.py --list

# Evaluate a scenario
python pam_world.py --scenario global_war_risk --simulate 5000 --explain

# Evaluate with country context
python pam_world.py --country "Ukraine" --scenario civil_war_risk

# Run all scenarios
python pam_world.py --run-all

# Health check
python pam_world.py --health

# Export data
python pam_world.py --export output.json

# View history
python pam_world.py --history global_war_risk

# Statistics
python pam_world.py --stats
```

### API Usage

```bash
# List scenarios
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/scenarios

# Evaluate scenario
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/api/v1/evaluate/global_war_risk?simulate=5000"

# Get signal values
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/signals

# Get history
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/api/v1/history/global_war_risk?days=30"
```

## Configuration

Edit `world_config.json` to customize:

- **Sources**: RSS/Atom feed URLs
- **Signals**: Signal definitions with weights and aggregation methods
- **Hypotheses**: Scenario definitions with priors and signal dependencies
- **Keywords**: Keyword sets for signal extraction
- **Signal Bindings**: Mapping signals to sources and keywords

See [Configuration Guide](docs/architecture.md#configuration) for details.

## Architecture

See [Architecture Documentation](docs/architecture.md) for system design, data flow, and component descriptions.

## Security

See [Security Documentation](docs/security.md) for security measures, best practices, and vulnerability mitigation.

## Deployment

See [Deployment Guide](docs/deployment.md) for production deployment instructions, Docker setup, and environment configuration.

## Testing

Run tests with coverage:

```bash
pytest --cov --cov-report=html
```

Coverage report will be in `htmlcov/index.html`.

## Project Structure

```
pam/
├── api/                 # FastAPI application
│   ├── main.py         # FastAPI app
│   ├── auth.py         # Authentication
│   └── routes/         # API routes
├── tests/              # Test suite
├── docs/               # Documentation
├── deploy/             # Deployment scripts
├── pam_world.py        # Main application
├── security.py         # Security utilities
├── validators.py       # Configuration validation
├── logger.py           # Logging configuration
├── metrics.py          # Metrics collection
├── health.py           # Health checks
├── cache.py            # Caching utilities
├── fetcher.py          # Parallel feed fetching
├── database.py         # Database operations
├── world_config.json   # Configuration file
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
└── requirements.txt    # Python dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure tests pass and coverage is maintained
6. Submit a pull request

## License

[Specify your license here]

## Disclaimer

⚠️ **IMPORTANT**: This is a decision-support tool. It is NOT a substitute for professional risk analysis or official alerts. It will produce noisy outputs. Use judgement and cross-check with trusted sources.

## Support

For issues, questions, or contributions, please open an issue on the repository.

