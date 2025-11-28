# Government of Canada Open Data MCP Servers

Python-based Model Context Protocol (MCP) servers for accessing Canada's Open Government data. This project includes two complementary MCP servers:

1. **GOV CA DATASET MCP** - Universal dataset discovery, search, and metadata retrieval across all Canadian government open data
2. **GOV CA TRANSPORTATION MCP** - Specialized infrastructure querying for bridges, airports, cycling networks, transit, railways, and tunnels

## Features

### Dataset Discovery (gov_mcp)
- Search across **250,000+ datasets** from Open Government Canada
- Browse by topic, organization, or jurisdiction (federal/provincial/municipal)
- Get detailed dataset schemas and download URLs
- Track recent dataset updates

### Transportation Infrastructure (gov_ca_transportation)
- Query **bridge conditions** with filtering by province, city, and condition rating
- Search **airports** across Canada with facility details
- Explore **cycling networks** in major cities (Vancouver, Toronto, Montreal, etc.)
- Access **transit stops** and coverage analysis
- Query **railway** infrastructure
- Search **tunnels** by province and type

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
├── server.py                     # MCP server with 10+ tools
├── api_client.py                 # Direct data fetching from provincial/municipal sources
├── http_client.py                # HTTP client
└── types.py                      # Type definitions
```

## Data Sources

The Transportation MCP fetches **actual infrastructure records** from:

| Province | Bridges | Airports | Cycling | Transit |
|----------|---------|----------|---------|---------|
| British Columbia | ✅ BC OpenMaps WFS | ✅ BC OpenMaps WFS | ✅ Vancouver Open Data | - |
| Ontario | ✅ Ontario Open Data | - | ✅ Toronto Open Data | ✅ TTC GTFS |
| Quebec | ✅ Montreal Open Data | ✅ Quebec WFS | ✅ Montreal/Quebec City | ✅ STM |
| Nova Scotia | ✅ NS Open Data | - | - | - |
| National | - | - | - | ✅ Multiple agencies |

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

### Transportation Infrastructure MCP (gov_ca_transportation) - 10 Tools

| Tool | Description |
|------|-------------|
| `query_bridges` | Search bridge infrastructure by province, city, condition |
| `analyze_bridge_conditions` | Aggregate condition analysis for a region |
| `query_ports_airports` | Search airports, ports, marinas, heliports |
| `query_cycling_networks` | Get cycling paths and lanes by municipality |
| `query_transit_stops` | Search public transit stops by city |
| `analyze_transit_coverage` | Analyze transit accessibility coverage |
| `get_gtfs_feed` | Access transit data in GTFS format |
| `query_railways` | Search railway lines and stations |
| `query_tunnels` | Search tunnel infrastructure |
| `compare_across_regions` | Compare infrastructure across provinces |
| `get_infrastructure_costs` | Get replacement cost estimates |

## Example Usage

### Search for Datasets
```python
# Search for water datasets in Saskatchewan
result = search_datasets(query="water Saskatchewan", limit=20)
# Returns 103 datasets including water quality monitoring data
```

### Analyze Bridge Conditions
```python
# Get Montreal bridge conditions
result = analyze_bridge_conditions(region="Montreal", limit=100)
# Returns condition analysis for 577 road structures
```

### Query Cycling Networks
```python
# Get Vancouver bikeways
result = query_cycling_networks(municipality="Vancouver", limit=50)
# Returns cycling paths with route names, types, surface info
```

### Get Tax Datasets
```python
# Search federal tax datasets  
result = search_datasets(query="tax income", jurisdiction="federal", limit=20)
# Returns 530 datasets from CRA and Statistics Canada
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
│   ├── api_client.py           # Direct data fetcher
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
- **Real infrastructure data** from provincial/municipal open data portals
- **Multi-province coverage**: BC, Ontario, Quebec, Nova Scotia, and more
- **Multiple data formats**: GeoJSON, CSV, WFS, ESRI REST
- **Condition analysis**: Bridge ICG ratings, age distribution, critical structures
- **Geographic filtering**: By province, city, or region

## API Sources

| Source | Data Types |
|--------|------------|
| open.canada.ca | Federal datasets, Statistics Canada |
| donnees.montreal.ca | Montreal infrastructure, cycling |
| data.ontario.ca | Ontario bridges, transit |
| openmaps.gov.bc.ca | BC airports, bridges, railways |
| opendata.vancouver.ca | Vancouver bikeways |
| data.novascotia.ca | Nova Scotia structures |
| donneesquebec.ca | Quebec provincial data |

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request
