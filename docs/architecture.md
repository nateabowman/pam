# World P.A.M. Architecture

## Overview

World P.A.M. is a modular system for analyzing geopolitical risk through RSS/Atom feed analysis. The architecture is designed for scalability, security, and maintainability.

## System Components

### Core Components

1. **Feed Fetcher** (`fetcher.py`)
   - Parallel HTTP requests using ThreadPoolExecutor
   - TTL-based caching
   - Rate limiting and error handling

2. **Signal Processor** (`pam_world.py`)
   - Keyword extraction and matching
   - Date-based filtering
   - Signal normalization (0.0 to 1.0)

3. **Hypothesis Evaluator** (`pam_world.py`)
   - Logistic model computation
   - Monte Carlo simulation
   - Probability estimation

4. **Database** (`database.py`)
   - SQLite for persistence
   - Historical data tracking
   - Export capabilities

5. **API Server** (`api/main.py`)
   - FastAPI REST API
   - Authentication middleware
   - Web dashboard

### Supporting Components

- **Security** (`security.py`): URL validation, rate limiting, XML protection
- **Validation** (`validators.py`): Configuration validation, date parsing
- **Logging** (`logger.py`): Structured logging with rotation
- **Metrics** (`metrics.py`): Performance metrics collection
- **Health** (`health.py`): Health check system
- **Cache** (`cache.py`): TTL-based caching

## Data Flow

```
┌─────────────┐
│ RSS/Atom    │
│ Feeds       │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│ Feed        │──────▶│ Cache       │
│ Fetcher     │      │ (TTL)       │
└──────┬──────┘      └─────────────┘
       │
       ▼
┌─────────────┐
│ XML Parser  │
│ (Secure)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Keyword     │
│ Matcher     │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│ Signal      │──────▶│ Database    │
│ Computer    │      │ (SQLite)    │
└──────┬──────┘      └─────────────┘
       │
       ▼
┌─────────────┐
│ Hypothesis  │
│ Evaluator   │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│ REST API    │◀─────│ Web         │
│ (FastAPI)   │      │ Dashboard   │
└─────────────┘      └─────────────┘
```

## Configuration

### Configuration File Structure

`world_config.json` contains:

- **sources**: RSS/Atom feed definitions
- **signals**: Signal definitions with weights
- **hypotheses**: Scenario definitions
- **keyword_sets**: Named keyword lists
- **signal_bindings**: Signal-to-source/keyword mappings

### Signal Computation

1. Fetch feeds from configured sources (parallel)
2. Parse XML/Atom content
3. Match keywords in title/summary
4. Filter by date window
5. Normalize with sqrt dampening
6. Aggregate (sum or max)
7. Apply cap

### Hypothesis Evaluation

1. Start with prior probability
2. Convert to logit space
3. Add weighted signal contributions
4. Convert back to probability (sigmoid)
5. Optionally run Monte Carlo simulation

## Security Architecture

- **URL Validation**: Whitelist-based URL validation
- **Rate Limiting**: Per-domain rate limiting
- **XML Protection**: Size limits and entity expansion protection
- **Input Validation**: Configuration schema validation
- **Request Size Limits**: Maximum response size limits

## Performance Optimizations

- **Parallel Fetching**: ThreadPoolExecutor for concurrent requests
- **Caching**: TTL-based caching for feeds, configs, signals
- **Connection Reuse**: HTTP connection pooling
- **Database Indexing**: Indexed queries for fast retrieval

## Scalability

- **Stateless API**: API can be horizontally scaled
- **Database**: SQLite suitable for single-instance; can migrate to PostgreSQL
- **Caching**: In-memory cache; can use Redis for distributed caching
- **Worker Processes**: Can run separate worker processes for feed fetching

## Monitoring

- **Health Checks**: `/health` endpoint
- **Metrics**: Request counts, latencies, error rates
- **Logging**: Structured logging with rotation
- **Database Stats**: Query performance tracking

## Deployment Architecture

```
┌─────────────┐
│ Load        │
│ Balancer    │
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ API      │   │ API      │   │ API      │
│ Instance │   │ Instance │   │ Instance │
└────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │
     └──────────────┴──────────────┘
                    │
                    ▼
            ┌──────────────┐
            │ Database      │
            │ (SQLite/      │
            │  PostgreSQL)  │
            └──────────────┘
```

## Future Enhancements

- Machine learning model integration
- Real-time streaming feeds
- Multi-language support
- Advanced visualization
- Alert system
- Distributed caching (Redis)
- Message queue for async processing

