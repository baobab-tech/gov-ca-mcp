# Government of Canada Open Data MCP Servers

Python-based Model Context Protocol (MCP) servers for accessing Canada's Open Government data. This project includes two complementary MCP servers:

1. **GOV CA DATASET MCP** - Universal dataset discovery, search, and metadata retrieval across all Canadian government open data
2. **GOV CA TRANSPORTATION MCP** - Specialized infrastructure querying for bridges, tunnels, airports, ports, and railways with Statistics Canada cost data

## Features

### Dataset Discovery (gov_mcp)
- Search across **250,000+ datasets** from Open Government Canada
- Browse by topic, organization, or jurisdiction (federal/provincial/municipal)
- Get detailed dataset schemas and download URLs
- Track recent dataset updates

### Transportation Infrastructure (gov_ca_transportation)
- Query **bridge conditions** using Statistics Canada national data for all provinces
- Get **infrastructure replacement costs** from Statistics Canada surveys
- Search **airports and ports** across Canada
- Query **railway** infrastructure
- Search **tunnels** by province and type
- **Unified data approach**: Uses Statistics Canada Core Public Infrastructure Survey for consistent national coverage

## Quick Start

### Installation

```bash
# Clone and install
cd gov_mcp
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Running the Servers

```bash
# Dataset Discovery MCP
python -m gov_mcp.server

# Transportation Infrastructure MCP  
python -m gov_ca_transportation.server
```

## Architecture

```
gov_mcp/                          # Dataset Discovery MCP
├── server.py                     # MCP server with 7 tools
├── api_client.py                 # Open Government Canada API wrapper
├── http_client.py                # HTTP client with retry logic
└── types.py                      # Type definitions

gov_ca_transportation/            # Transportation Infrastructure MCP
├── server.py                     # MCP server with 7 tools
├── api_client.py                 # Statistics Canada + provincial data fetching
├── http_client.py                # HTTP client
└── types.py                      # Type definitions
```

## Data Sources

The Transportation MCP uses **Statistics Canada** as the primary data source for national coverage:

| Data Type | Primary Source | Coverage |
|-----------|---------------|----------|
| Bridge Conditions | Statistics Canada Table 34-10-0288-01 | All provinces/territories |
| Infrastructure Costs | Statistics Canada Table 34-10-0284-01 | All provinces/territories |
| Detailed Bridge Records | Provincial Open Data | Ontario, Quebec, Nova Scotia |
| Airports | Quebec Open Data, BC OpenMaps | Quebec, British Columbia |
| Railways | National Railway Network | National |

## Available Tools

### Dataset Discovery MCP (gov_mcp) - 7 Tools

| Tool | Description |
|------|-------------|
| `search_datasets` | Search across all 250,000+ Canadian government datasets |
| `get_dataset_schema` | Get complete schema with field definitions and download URLs |
| `list_organizations` | Browse by department/organization |
| `browse_by_topic` | Explore datasets by subject area |
| `check_available_mcps` | Check which specialized MCPs are available |
| `get_activity_stream` | See recently updated datasets |
| `query_datastore` | Query data directly (fallback mode) |

### Transportation Infrastructure MCP (gov_ca_transportation) - 7 Tools

| Tool | Description |
|------|-------------|
| `query_bridges` | Search bridge infrastructure by province with StatCan condition data |
| `analyze_bridge_conditions` | Aggregate condition analysis using Statistics Canada data |
| `get_infrastructure_costs` | Get replacement costs by condition from Statistics Canada |
| `query_ports_airports` | Search airports, ports, marinas, heliports |
| `query_railways` | Search railway lines and stations |
| `query_tunnels` | Search tunnel infrastructure |
| `compare_across_regions` | Compare infrastructure across provinces |

## Example Usage

### Search for Datasets
```python
# Search for water datasets in Saskatchewan
result = search_datasets(query="water Saskatchewan", limit=20)
# Returns 103 datasets including water quality monitoring data
```

### Analyze Bridge Conditions
```python
# Get bridge conditions for any province using Statistics Canada data
result = analyze_bridge_conditions(region="Saskatchewan")
# Returns: Very Poor: 2.4%, Poor: 16.4%, Fair: 23.7%, Good: 32.4%, Very Good: 10.1%
```

### Get Infrastructure Costs
```python
# Get bridge replacement costs for Ontario
result = get_infrastructure_costs(infrastructure_type="bridge", location="Ontario")
# Returns: Total $81.4B, Priority investment needed: $2.65B (Poor + Very Poor)
```

### Query Bridges
```python
# Get bridge data with StatCan condition distribution
result = query_bridges(province="Ontario", limit=100)
# Returns condition summary + detailed records from provincial sources
```

## Project Structure

```
gov_mcp/
├── gov_mcp/                    # Dataset Discovery MCP
│   ├── __init__.py
│   ├── server.py               # MCP server
│   ├── api_client.py           # API wrapper
│   ├── http_client.py          # HTTP client
│   └── types.py                # Type definitions
├── gov_ca_transportation/      # Transportation MCP
│   ├── __init__.py
│   ├── server.py               # MCP server
│   ├── api_client.py           # StatCan + provincial data fetcher
│   ├── http_client.py          # HTTP client
│   └── types.py                # Type definitions
├── tests/                      # Test files
├── documentation/              # Additional docs
├── pyproject.toml              # Project config
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## Configuration

### VS Code MCP Settings

Add to your VS Code settings.json or MCP config:

```json
{
  "mcpServers": {
    "gov-ca-dataset": {
      "command": "python",
      "args": ["-m", "gov_mcp.server"],
      "cwd": "/path/to/gov_mcp"
    },
    "gov-ca-transportation": {
      "command": "python", 
      "args": ["-m", "gov_ca_transportation.server"],
      "cwd": "/path/to/gov_mcp"
    }
  }
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Running Validation

```bash
python validate.py
```

## Key Capabilities

- **250,000+ datasets** searchable from Open Government Canada
- **Statistics Canada integration** for authoritative national infrastructure data
- **All provinces covered** for bridge conditions and infrastructure costs
- **Real infrastructure data** from provincial/municipal open data portals
- **Multiple data formats**: GeoJSON, CSV, ZIP (StatCan)
- **Condition analysis**: Bridge condition percentages, replacement costs by condition
- **Geographic filtering**: By province or national aggregate

## API Sources

| Source | Data Types |
|--------|------------|
| Statistics Canada | Infrastructure costs, bridge conditions (national) |
| open.canada.ca | Federal datasets |
| donnees.montreal.ca | Montreal bridge records |
| data.ontario.ca | Ontario bridge records |
| openmaps.gov.bc.ca | BC airports, railways |
| data.novascotia.ca | Nova Scotia structures |
| donneesquebec.ca | Quebec airports |

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request
