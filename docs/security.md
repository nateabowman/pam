# Security Documentation

## Security Measures

World P.A.M. implements multiple security layers to protect against common vulnerabilities.

### 1. Server-Side Request Forgery (SSRF) Protection

**Implementation**: `security.py::validate_url()`

- URL scheme validation (only http/https allowed)
- Localhost and private IP blocking
- Network location whitelisting
- Hostname validation

**Configuration**: Allowed network locations are automatically extracted from configuration sources.

### 2. XML Bomb Protection

**Implementation**: `security.py::parse_xml_secure()`

- Maximum content size limits (10MB default)
- Entity expansion depth limits
- Iterative parsing with depth checks

### 3. Rate Limiting

**Implementation**: `security.py::check_rate_limit()`

- Per-domain rate limiting
- Configurable limits (10 requests per 60 seconds default)
- Prevents abuse and DoS attacks

### 4. Request Size Limits

**Implementation**: `security.py::fetch_url_secure()`

- Maximum response size: 10MB
- Content-Length header validation
- Chunked reading with size checks

### 5. Input Validation

**Implementation**: `validators.py::validate_config()`

- Configuration schema validation
- Reference integrity checks
- Type validation
- Range validation (probabilities, timeouts, etc.)

### 6. Exception Handling

- Specific exception types (URLError, HTTPError, ParseError)
- No broad `except Exception` in critical paths
- Proper error logging without exposing sensitive data

### 7. API Authentication

**Implementation**: `api/auth.py`

- API key authentication
- Header-based authentication (X-API-Key)
- Environment variable support for keys

### 8. CORS Configuration

**Implementation**: `api/main.py`

- Configurable CORS origins
- Environment variable based
- Default: permissive (change for production)

## Security Best Practices

### Production Deployment

1. **API Keys**:
   - Use strong, randomly generated API keys
   - Store in environment variables or secret management
   - Rotate keys regularly
   - Never commit keys to version control

2. **CORS**:
   - Restrict CORS origins to specific domains
   - Do not use wildcard (`*`) in production

3. **Database**:
   - Use file permissions to restrict database access
   - Regular backups
   - Consider encryption at rest

4. **Logging**:
   - Do not log sensitive data (API keys, passwords)
   - Rotate logs regularly
   - Monitor logs for suspicious activity

5. **Network**:
   - Use HTTPS in production
   - Implement firewall rules
   - Use reverse proxy (nginx, traefik) for additional security

6. **Updates**:
   - Keep dependencies updated
   - Monitor security advisories
   - Apply patches promptly

### Environment Variables

Secure environment variables:

```bash
# Required
PAM_API_KEY=<strong-random-key>

# Recommended
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
```

### Docker Security

- Run containers as non-root user
- Use read-only filesystems where possible
- Limit container resources
- Scan images for vulnerabilities
- Use secrets management (Docker secrets, Kubernetes secrets)

## Vulnerability Reporting

If you discover a security vulnerability, please:

1. **Do not** open a public issue
2. Email security details to [security contact]
3. Include steps to reproduce
4. Allow time for fix before disclosure

## Security Checklist

- [ ] API keys are strong and stored securely
- [ ] CORS is properly configured
- [ ] Database is protected with proper permissions
- [ ] Logs do not contain sensitive information
- [ ] Dependencies are up to date
- [ ] HTTPS is enabled in production
- [ ] Rate limiting is configured appropriately
- [ ] URL whitelist is properly maintained
- [ ] Health checks are monitored
- [ ] Backups are encrypted and tested

## Known Limitations

1. **SQLite**: Single-instance database; consider PostgreSQL for multi-instance deployments
2. **In-Memory Cache**: Not shared across instances; consider Redis for distributed caching
3. **Rate Limiting**: Per-process; consider distributed rate limiting for multi-instance deployments

## Security Updates

Security updates are documented in [CHANGELOG.md](../CHANGELOG.md) with `[SECURITY]` tags.

