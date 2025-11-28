# Architecture Documentation - Government MCP Server v0.1.0

## Overview

The Government MCP Server is a Python-based Model Context Protocol server that provides universal access to Canada's Open Government infrastructure datasets. It acts as the core/foundation MCP that all users install first, offering dataset discovery, metadata retrieval, and intelligent routing to specialized MCPs.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Client                              │
│                      (Claude/AI Agent)                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                        Tool Calls (JSON-RPC)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GovernmentMCPServer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             Tool Request Handler                        │  │
│  │  • search_all_infrastructure                            │  │
│  │  • get_dataset_schema                                   │  │
│  │  • list_organizations                                   │  │
│  │  • browse_by_topic                                      │  │
│  │  • check_available_mcps                                 │  │
│  │  • get_activity_stream                                  │  │
│  │  • basic_datastore_query                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                     API Calls (Structured)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              OpenGovCanadaClient                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   • Data search and filtering                           │  │
│  │   • Schema extraction                                   │  │
│  │   • Activity tracking                                   │  │
│  │   • MCP routing logic                                   │  │
│  │   • Result normalization                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                      HTTP Requests
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 HTTPClient (with Retry)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Automatic retry logic (exponential backoff)          │  │
│  │  • Session management                                   │  │
│  │  • Error handling                                        │  │
│  │  • Timeout management                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                          HTTPS
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│        Open Government Canada API (CKAN)                        │
│        https://open.canada.ca/data/api                         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. GovernmentMCPServer (`server.py`)

**Purpose:** Main MCP server that handles tool registration and request dispatching.

**Key Responsibilities:**
- Initialize and configure the MCP server
- Register all 7 available tools
- Handle incoming tool calls from MCP clients
- Convert tool results to MCP-compatible format
- Error handling and logging

**Key Methods:**
```python
def __init__()              # Initialize server with tools
async def handle_tool_call()  # Process tool requests
async def run()             # Start the server
```

**Tool Handlers:**
- `_handle_search()` → search_all_infrastructure
- `_handle_schema()` → get_dataset_schema
- `_handle_organizations()` → list_organizations
- `_handle_browse_topic()` → browse_by_topic
- `_handle_check_mcps()` → check_available_mcps
- `_handle_activity_stream()` → get_activity_stream
- `_handle_datastore_query()` → basic_datastore_query

### 2. OpenGovCanadaClient (`api_client.py`)

**Purpose:** Wraps the Open Government Canada API (CKAN-based) and implements core business logic.

**Key Responsibilities:**
- Execute dataset searches with filters
- Retrieve and normalize dataset schemas
- Manage organization browsing
- Track dataset activity/updates
- Implement MCP routing logic
- Handle API response transformation

**Key Methods:**
```python
def search_all_infrastructure()    # Search datasets
def get_dataset_schema()           # Retrieve schema
def list_organizations()           # List organizations
def browse_by_topic()              # Explore by topic
def get_activity_stream()          # Get recent updates
def basic_datastore_query()        # Query data
def _determine_mcp()               # MCP routing logic
```

**MCP Routing Logic:**
Based on dataset tags and content, recommends specialized MCPs:
- `climate-mcp` → Climate, environment, emissions
- `health-mcp` → Health, disease, medical
- `transportation-mcp` → Transportation, traffic, roads
- `economic-mcp` → Economics, trade, business

### 3. HTTPClient (`http_client.py`)

**Purpose:** Provides reliable HTTP communication with automatic retry logic.

**Key Responsibilities:**
- Create sessions with retry strategies
- Execute GET and POST requests
- Implement exponential backoff retry logic
- Handle timeouts and connection errors
- Maintain request/response logging

**Key Features:**
- Automatic retry on 5xx errors
- Configurable backoff factor
- Request timeout handling
- Session reuse and pooling
- Error logging

**Configuration:**
```python
@dataclass
class RetryConfig:
    max_retries: int = 3           # Max retry attempts
    backoff_factor: float = 1.0    # Exponential backoff multiplier
    timeout: int = 30              # Request timeout in seconds
    status_forcelist: tuple = (500, 502, 504)  # Status codes to retry
```

### 4. Type Definitions (`types.py`)

**Purpose:** Provide structured data types for type safety and IDE support.

**Key Types:**
- `Resource` - Dataset resource (file/API)
- `Organization` - Government organization
- `Dataset` - Complete dataset definition
- `DatasetMetadata` - Simplified metadata
- `SearchResult` - Search result with routing
- `ActivityUpdate` - Recent activity tracking
- `MCPStatus` - Specialized MCP status

## Data Flow Examples

### Example 1: Search Workflow

```
Client: search_all_infrastructure("water infrastructure")
  ↓
GovernmentMCPServer.handle_tool_call()
  ↓
OpenGovCanadaClient.search_all_infrastructure()
  ↓
OpenGovCanadaClient._determine_mcp()  [Analyze tags]
  ↓
HTTPClient.get("3/action/package_search", params={q: "water infrastructure"})
  ↓
Retry Logic: If 5xx error → exponential backoff retry
  ↓
API Response: JSON with matching datasets
  ↓
Transform to SearchResult with recommended MCP
  ↓
Return to Client
```

### Example 2: Schema Retrieval Workflow

```
Client: get_dataset_schema("dataset-id-123")
  ↓
GovernmentMCPServer.handle_tool_call()
  ↓
OpenGovCanadaClient.get_dataset_schema(dataset_id)
  ↓
HTTPClient.get("3/action/package_show", params={id: dataset-id-123})
  ↓
Extract resources and format information
  ↓
Return normalized schema
  ↓
Return to Client
```

## Tool Specifications

### Tool 1: search_all_infrastructure

```
Input:
  query (string, required) - Search query
  type (string, optional) - Filter by type
  location (string, optional) - Filter by location
  limit (integer, optional) - Max results (default 10)

Output:
  count: number of results
  datasets: [{id, title, organization, description, tags, resource_count}]
  recommended_mcp: string or null
  note: routing guidance
```

**Implementation Logic:**
1. Build search parameters from inputs
2. Make API call to package_search endpoint
3. Extract and normalize results
4. Analyze tags for MCP recommendation
5. Return structured result

---

### Tool 2: get_dataset_schema

```
Input:
  dataset_id (string, required) - Unique dataset identifier

Output:
  schema:
    dataset_id: string
    title: string
    description: string
    organization: string
    resources: [{id, name, format, url, description}]
  note: usage guidance
```

**Implementation Logic:**
1. Call package_show endpoint with dataset ID
2. Extract resource and metadata information
3. Structure schema with field definitions
4. Return complete schema

---

### Tool 3: list_organizations

```
Input:
  filter (string, optional) - Text filter

Output:
  count: number of organizations
  organizations: [{id, name, title, packages}]
```

**Implementation Logic:**
1. Call organization_list endpoint
2. Apply optional text filter
3. Include package counts
4. Return organized list

---

### Tool 4: browse_by_topic

```
Input:
  topic (string, required) - Topic/subject area

Output:
  topic: string
  count: number of datasets
  datasets: [{id, title, organization, tags}]
```

**Implementation Logic:**
1. Search with topic as tag filter
2. Gather matching datasets
3. Return grouped by topic

---

### Tool 5: check_available_mcps

```
Input: (none)

Output:
  core_mcp:
    name: string
    available: boolean
    version: string
  specialized_mcps: {
    [mcp_id]: {name, available, version, capabilities}
  }
  note: installation guidance
```

**Implementation Logic:**
1. Report core MCP status (always available)
2. List known specialized MCPs with status
3. Indicate installation requirements

---

### Tool 6: get_activity_stream

```
Input:
  organization (string, optional) - Filter by org
  limit (integer, optional) - Max updates (default 20)

Output:
  count: number of updates
  updates: [{dataset_id, dataset_title, organization, timestamp, action}]
```

**Implementation Logic:**
1. Search recent datasets with optional org filter
2. Sort by timestamp descending
3. Limit results
4. Return activity updates

---

### Tool 7: basic_datastore_query

```
Input:
  resource_id (string, required) - Resource ID
  filters (object, optional) - Query filters
  limit (integer, optional) - Max records (default 100)

Output:
  resource_id: string
  records: array of records
  total: number of total records
  limit: applied limit
  note: usage guidance
```

**Implementation Logic:**
1. Call datastore_search endpoint
2. Apply optional filters
3. Limit results to max 1000
4. Return query results

## Error Handling Strategy

### HTTP Level
- **Connection Errors**: Automatic retry with exponential backoff
- **Timeout Errors**: Configurable timeout with retry
- **5xx Errors**: Automatic retry up to max_retries
- **4xx Errors**: Fail immediately with descriptive error

### API Level
- **Invalid Dataset ID**: Return error message
- **Missing Parameters**: Validate and return error
- **API Rate Limits**: Handle 429 responses with retry
- **Malformed Responses**: Log and return structured error

### MCP Level
- All errors returned with descriptive messages
- Error flag set in ToolResult
- Stack traces logged for debugging
- User-friendly error messages

## Configuration & Deployment

### Environment Variables
```bash
# Optional configuration (defaults provided)
GOV_MCP_TIMEOUT=30
GOV_MCP_MAX_RETRIES=3
GOV_MCP_LOG_LEVEL=INFO
```

### Installation
```bash
# Development installation
pip install -e .

# Production installation
pip install .
```

### Running the Server
```bash
# Using Python module
python -m gov_mcp.server

# Using installed command
gov-mcp-server

# With custom logging
LOG_LEVEL=DEBUG python -m gov_mcp.server
```

## Performance Considerations

### Caching Strategy (Future v0.2.0)
- Cache organization list (1 hour TTL)
- Cache dataset schemas (2 hour TTL)
- Cache topic browse results (30 min TTL)
- No cache for search/activity (real-time)

### Optimization Opportunities
- Parallel requests for multiple endpoints
- Response compression for large results
- Connection pooling (already implemented)
- Query result pagination

### Resource Usage
- Memory: ~50-100MB baseline
- Network: ~1-5MB per active session
- CPU: Minimal (mostly I/O bound)

## Testing Strategy

### Unit Tests
- HTTPClient retry logic
- API response parsing
- Type validation
- Error handling

### Integration Tests
- End-to-end tool execution
- API endpoint connectivity
- Error recovery scenarios

### Manual Testing
```bash
# Run validation
python validate.py

# Run examples
python examples.py

# Start server for interactive testing
python -m gov_mcp.server
```

## Future Enhancements (v0.2.0+)

### Phase 1: Stability & Performance
- [ ] Response caching layer
- [ ] Query optimization
- [ ] Comprehensive logging
- [ ] Performance metrics

### Phase 2: Features
- [ ] Advanced filtering syntax
- [ ] Dataset recommendations
- [ ] Custom alerts/monitoring
- [ ] Export capabilities

### Phase 3: Integration
- [ ] Specialized MCP registration
- [ ] Federation support
- [ ] Custom API endpoints
- [ ] Webhook support

## Maintenance & Support

### Logging
All components log to stderr with format:
```
TIMESTAMP - COMPONENT - LEVEL - MESSAGE
```

### Monitoring
- Track API response times
- Monitor retry rates
- Alert on repeated failures
- Log all tool executions

### Debugging
```bash
# Enable debug logging
DEBUG=true python -m gov_mcp.server

# Test specific tool
python -c "from gov_mcp.api_client import OpenGovCanadaClient; ..."
```

## References

- MCP Documentation: https://modelcontextprotocol.io/
- CKAN API: https://docs.ckan.org/en/latest/api/
- Open Government Canada: https://open.canada.ca/data/api
- Python Requests: https://docs.python-requests.org/
