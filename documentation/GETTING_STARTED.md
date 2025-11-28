# Getting Started Guide

## What is the Government MCP Server?

The Government MCP Server is a Model Context Protocol (MCP) server written in Python that provides AI assistants (like Claude) with access to Canada's Open Government infrastructure datasets. It's the **core/foundation MCP** that everyone installs first.

## Key Features

✨ **Universal Search** - Search across all infrastructure datasets  
🎯 **Smart Routing** - Automatically recommend specialized MCPs  
📊 **Metadata Provider** - Get complete schema and resource information  
🔄 **Activity Tracking** - See recent dataset updates  
🏢 **Organization Browser** - Explore by department  
💾 **Fallback Querying** - Basic data queries when specialized MCPs unavailable  
🔁 **Retry Logic** - Automatic error recovery with exponential backoff  

## Installation

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Step 1: Clone or Navigate to Project

```bash
cd /Users/krunal/Desktop/gov_mcp
```

### Step 2: Install Dependencies

```bash
# Development installation (editable mode)
pip install -e .

# Or with production dependencies only
pip install .
```

This will install:
- `requests` - HTTP client
- `pydantic` - Data validation
- `mcp` - Model Context Protocol SDK

### Step 3: Verify Installation

```bash
python validate.py
```

You should see all validation checks pass with ✓ marks.

## Quick Start

### Starting the Server

```bash
# Method 1: Using Python module
python -m gov_mcp.server

# Method 2: Using installed command
gov-mcp-server

# Method 3: With debug logging
DEBUG=true python -m gov_mcp.server
```

The server will start and listen for tool calls from MCP clients.

### Testing with Examples

```bash
python examples.py
```

This runs example queries showing each tool in action.

## Understanding the 7 Tools

### 1. Search Infrastructure 🔍

Find datasets across Canada's open government data.

**When to use:** Looking for specific infrastructure data (water, roads, energy, etc.)

```python
from gov_mcp.api_client import OpenGovCanadaClient

client = OpenGovCanadaClient()
results = client.search_all_infrastructure(
    query="water infrastructure",
    limit=10
)
print(f"Found {results.count} datasets")
print(f"Recommended MCP: {results.recommended_mcp}")
```

---

### 2. Get Schema 📋

Understand the structure of any dataset before querying.

**When to use:** Need to know available fields and formats in a dataset

```python
schema = client.get_dataset_schema("water-quality-stations")
print(f"Dataset: {schema['title']}")
for resource in schema['resources']:
    print(f"  Format: {resource['format']}, URL: {resource['url']}")
```

---

### 3. List Organizations 🏢

Browse government departments and agencies.

**When to use:** Want to see datasets from specific departments

```python
orgs = client.list_organizations(filter="environment")
for org in orgs:
    print(f"{org['title']} - {org['packages']} datasets")
```

---

### 4. Browse Topics 🗂️

Explore datasets by subject area.

**When to use:** Interested in exploring a topic area broadly

```python
climate_data = client.browse_by_topic("climate")
print(f"Found {climate_data['count']} climate datasets")
```

---

### 5. Check MCPs ✅

See which specialized MCPs are available.

**When to use:** Determining if specialized tools are installed

```python
status = client.check_available_mcps()
# Shows core + any installed specialized MCPs
```

---

### 6. Activity Stream 📡

See what datasets have been updated recently.

**When to use:** Staying updated on government data changes

```python
updates = client.get_activity_stream(limit=20)
for update in updates:
    print(f"[{update.action}] {update.dataset_title}")
```

---

### 7. Basic Query 💾

Query data directly when specialized MCP not available.

**When to use:** Need simple data access without specialized tools

```python
results = client.basic_datastore_query(
    resource_id="air-quality-stations",
    filters={"province": "Ontario"},
    limit=100
)
```

## Project Structure

```
gov_mcp/
├── __init__.py              # Package entry point
├── types.py                 # Type definitions
├── http_client.py           # HTTP client with retry
├── api_client.py            # Open Government API wrapper
└── server.py                # Main MCP server

pyproject.toml               # Project configuration
requirements.txt             # Python dependencies
examples.py                  # Usage examples
validate.py                  # Validation script
README.md                    # Full documentation
ARCHITECTURE.md              # Technical details
GETTING_STARTED.md           # This file
```

## Configuration

### Retry Settings

The HTTP client automatically retries failed requests with exponential backoff:

- **Max Retries:** 3 (configurable)
- **Backoff Factor:** 1.0 (multiplies with retry count)
- **Timeout:** 30 seconds
- **Retryable Status Codes:** 500, 502, 504

### Custom Configuration

```python
from gov_mcp.http_client import RetryConfig
from gov_mcp.api_client import OpenGovCanadaClient

config = RetryConfig(
    max_retries=5,
    backoff_factor=2.0,
    timeout=60
)

client = OpenGovCanadaClient(retry_config=config)
```

## Common Use Cases

### Use Case 1: Find All Transportation Datasets

```python
client = OpenGovCanadaClient()

# Search for transportation
results = client.search_all_infrastructure(
    query="transportation infrastructure"
)

# Check recommended MCP
print(f"Use {results.recommended_mcp} for advanced analysis")

# Browse the results
for dataset in results.datasets[:5]:
    print(f"- {dataset['title']} ({dataset['organization']})")
```

### Use Case 2: Get Recent Environmental Data Updates

```python
# See what's been updated recently
updates = client.get_activity_stream(limit=10)

# Filter for environment-related
env_updates = [u for u in updates if 'environment' in u.organization.lower()]

for update in env_updates:
    print(f"Updated: {update.dataset_title} ({update.timestamp})")
```

### Use Case 3: Query Health Statistics

```python
# Search for health data
results = client.search_all_infrastructure(query="health statistics")

if results.datasets:
    # Get the first dataset's schema
    dataset_id = results.datasets[0]['id']
    schema = client.get_dataset_schema(dataset_id)
    
    # Query the data
    for resource in schema['resources']:
        if resource['format'].lower() == 'csv':
            data = client.basic_datastore_query(
                resource_id=resource['id'],
                limit=100
            )
```

## Troubleshooting

### Issue: "Module not found" errors

**Solution:** Install dependencies with pip install -e .

### Issue: API timeouts

**Solution:** Increase timeout in RetryConfig:
```python
config = RetryConfig(timeout=60)
client = OpenGovCanadaClient(retry_config=config)
```

### Issue: No results from search

**Solution:** Try broader search terms or browse by topic instead:
```python
results = client.browse_by_topic("water")
```

### Issue: Connection refused

**Solution:** Ensure Open Government Canada API is accessible:
```bash
curl https://open.canada.ca/data/api/3/action/package_search?q=test
```

## Development

### Running Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy gov_mcp/
```

### Code Formatting

```bash
black gov_mcp/
```

### Linting

```bash
flake8 gov_mcp/
```

## API Documentation Reference

For detailed API documentation:
- Open Government Canada API: https://open.canada.ca/data/api
- CKAN API Reference: https://docs.ckan.org/en/latest/api/

## Next Steps

1. **Run Examples**: `python examples.py` to see the server in action
2. **Explore Data**: Use the tools to discover datasets
3. **Integrate**: Connect this MCP to your AI assistant
4. **Install Specialized MCPs**: Add domain-specific MCPs as needed

## Support & Feedback

For issues, questions, or feedback:
1. Check the README.md and ARCHITECTURE.md documentation
2. Review examples.py for usage patterns
3. Run validate.py to diagnose issues
4. Check server logs for detailed error messages

## Version History

**v0.1.0** (Current)
- ✅ Core MCP server implementation
- ✅ All 7 tools implemented
- ✅ HTTP client with retry logic
- ✅ Complete documentation

**v0.2.0** (Planned)
- [ ] Response caching
- [ ] Performance optimization
- [ ] Advanced filtering
- [ ] Specialized MCP integration

## License

MIT License - See LICENSE file for details
