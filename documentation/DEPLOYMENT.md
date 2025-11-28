# DEPLOYMENT.md - Deployment & Operations Guide

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing (`pytest tests/`)
- [ ] Type checks passing (`mypy gov_mcp/`)
- [ ] Code formatted (`black gov_mcp/`)
- [ ] Lint checks passing (`flake8 gov_mcp/`)
- [ ] Documentation updated
- [ ] Version bumped in `pyproject.toml`

### Installation for Users

#### Option 1: Install from Source

```bash
git clone <repo>
cd gov_mcp
pip install -e .
```

#### Option 2: Install from Package (Future)

```bash
pip install gov-mcp-server
```

### Starting the Server

#### Standalone Mode

```bash
gov-mcp-server
```

#### With Claude/MCP Client

Configure in your MCP client (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "gov-infrastructure": {
      "command": "gov-mcp-server",
      "args": []
    }
  }
}
```

#### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["gov-mcp-server"]
```

## Configuration

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json|text             # Output format

# API Configuration
GOV_API_TIMEOUT=30               # Request timeout in seconds
GOV_API_MAX_RETRIES=3            # Maximum retry attempts
GOV_API_BACKOFF_FACTOR=1.0       # Backoff multiplier
```

### Configuration File Support (Future)

```yaml
# config.yaml
server:
  timeout: 30
  max_retries: 3
  
logging:
  level: INFO
  format: text
```

## Monitoring & Logging

### Log Format

```
2025-11-26 10:00:00 - gov_mcp.server - INFO - Tool called: search_all_infrastructure
2025-11-26 10:00:01 - gov_mcp.api_client - INFO - Making API call: package_search
2025-11-26 10:00:02 - gov_mcp.http_client - DEBUG - GET https://open.canada.ca/data/api/3/action/package_search
```

### Key Metrics to Monitor

```
- Tool execution time (ms)
- API response time (ms)
- Retry attempts per request
- Error rate (%)
- Active connections
```

### Health Check

```python
# Simple health check endpoint (future v0.2.0)
GET /health

Response:
{
  "status": "healthy",
  "version": "0.1.0",
  "api_reachable": true,
  "uptime_seconds": 3600
}
```

## Troubleshooting

### Server Won't Start

**Symptom:** ImportError or ModuleNotFoundError

**Solution:**
```bash
pip install -e .
python validate.py
```

### API Timeout Errors

**Symptom:** requests.exceptions.Timeout

**Solution:**
```bash
export GOV_API_TIMEOUT=60
gov-mcp-server
```

### No Results from Queries

**Symptom:** Empty dataset results

**Solution:**
1. Verify API connectivity: `curl https://open.canada.ca/data/api/3/action/package_search?q=test`
2. Check query syntax
3. Try broader search terms

### Retry Loop Detection

**Symptom:** Request keeps retrying

**Monitor:** Check retry counts in logs
```bash
gov-mcp-server 2>&1 | grep "retry"
```

**Solution:** Increase timeout or disable retries for specific endpoints

## Performance Tuning

### Connection Pooling

Already optimized in HTTPClient with requests.Session

### Response Caching (v0.2.0)

```python
# Cache TTLs (planned)
organizations: 3600s      # 1 hour
schemas: 7200s            # 2 hours
topics: 1800s             # 30 minutes
searches: no-cache        # Real-time
activity: 300s            # 5 minutes
```

### Batch Operations

Currently: Single requests per tool call

Future: Batch multiple searches in one request

## Backup & Recovery

### Configuration Backup

```bash
# Backup environment
env | grep GOV_ > config.backup
```

### Data Recovery

All data comes from open.canada.ca - no local data to backup

## Version Management

### Current Version

```bash
python -c "import gov_mcp; print(gov_mcp.__version__)"
```

### Version History Format

```
v0.1.0 - 2025-11-26
  - Core MCP server
  - All 7 tools
  - Retry logic
  
v0.2.0 - TBD
  - Caching
  - Performance optimization
```

### Upgrade Path

```bash
# v0.1.0 to v0.2.0
pip install --upgrade gov-mcp-server
```

## Security Considerations

### Current Status (v0.1.0)

- ✅ HTTPS-only communication
- ✅ No authentication required (read-only)
- ✅ No local data storage
- ✅ API-only interaction

### Future Security (v0.2.0+)

- [ ] API key support for advanced features
- [ ] Rate limiting
- [ ] Request logging/auditing
- [ ] Data validation schemas

### Data Privacy

- No user data collected
- No tracking or telemetry
- Only open government data accessed
- All data from public APIs

## Compliance

### Open Government

- ✅ Uses only public data sources
- ✅ No proprietary data
- ✅ Respects API terms of service
- ✅ Proper User-Agent headers

### Licensing

- MIT License on server code
- Uses open datasets only
- No license conflicts

## Support & SLA

### Support Channels

- GitHub Issues
- Documentation
- Code examples

### SLA (Best Effort v0.1.0)

- Availability: Best effort
- Response time: Community-based
- Bugs: Community patches welcome

### Escalation Path

1. Check documentation
2. Review examples.py
3. Check API status (https://open.canada.ca/data/api)
4. Open GitHub issue

## Operations Dashboard (Future)

```
Government MCP Server Dashboard
==============================
Status:        Running
Uptime:        12h 34m
Version:       0.1.0

API Stats:
  Requests:    1,234
  Avg Time:    250ms
  Errors:      2 (0.2%)
  Retries:     12

Active Connections: 3
Memory:            45MB
CPU:               <1%
```

## Maintenance Tasks

### Weekly

- [ ] Check error logs
- [ ] Monitor API response times
- [ ] Verify connectivity to API

### Monthly

- [ ] Review usage patterns
- [ ] Check for updates
- [ ] Validate tool functionality

### Quarterly

- [ ] Update dependencies
- [ ] Performance review
- [ ] Security audit

## Disaster Recovery

### Backup Scenario

Q: What if Open Government API goes down?

A: Server will return errors but continue running. Retry logic will keep attempting. Users should check API status.

### Data Loss Scenario

Q: Could user data be lost?

A: No local data is stored. Only caches (future) which can be regenerated.

## Roadmap for Operations

**v0.1.0** ✅
- Basic monitoring
- Error handling
- Logging

**v0.2.0** 📋
- Advanced metrics
- Performance optimization
- Caching strategies

**v1.0.0** 🚀
- Full observability
- SLA guarantees
- Enterprise support

## References

- Production Deployment: https://docs.python-guide.org/shipping/
- MCP Deployment: https://modelcontextprotocol.io/
- API Monitoring: https://open.canada.ca/data/api
