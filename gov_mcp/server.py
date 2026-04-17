"""
Main MCP server implementation for Canada's Open Government infrastructure.
Provides universal dataset search, metadata, and routing to specialized MCPs.

Supports both stdio and SSE transports:
- stdio: python -m gov_mcp.server
- SSE:   python -m gov_mcp.server --sse --port 8002
"""
import argparse
import json
import logging
import os
import sys
from typing import Any

# Parse args early to set port before FastMCP initialization
def _parse_args():
    parser = argparse.ArgumentParser(description="GOV CA Dataset MCP Server")
    parser.add_argument("--sse", action="store_true", help="Run with SSE transport (HTTP)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8002, help="Port to listen on (default: 8002)")
    # Only parse known args to avoid issues with other flags
    args, _ = parser.parse_known_args()
    return args

_args = _parse_args()

from mcp.server.fastmcp import FastMCP

from gov_mcp.api_client import OpenGovCanadaClient
from gov_mcp.http_client import RetryConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the MCP server using FastMCP with SSE config if needed
mcp = FastMCP(
    "gov-ca-dataset",
    instructions="GOV CA DATASET - Government of Canada Open Data MCP Server for searching and querying Canadian government datasets",
    host=_args.host,
    port=_args.port,
)

# Initialize API client
api_client = OpenGovCanadaClient(retry_config=RetryConfig(max_retries=3))


@mcp.tool()
def search_datasets(
    query: str,
    resource_format: str | None = None,
    jurisdiction: str | None = None,
    organization: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search across all infrastructure datasets in Canada.
    
    Args:
        query: Search query for datasets (e.g., 'water', 'climate', 'transportation')
        resource_format: Optional filter by data format. Common formats: CSV, JSON, XML, PDF, HTML, XLSX, GeoJSON, SHP, KML, WMS, API
        jurisdiction: Optional filter by jurisdiction level: 'federal', 'provincial', or 'municipal'
        organization: Optional filter by organization/department name (e.g., 'environment-and-climate-change-canada')
        limit: Maximum results to return (default 10, max 100)
    
    Returns:
        Dictionary containing search results with count, datasets, and recommended MCP
    """
    try:
        result = api_client.search_all_infrastructure(
            query=query,
            resource_format=resource_format,
            jurisdiction=jurisdiction,
            organization=organization,
            limit=min(limit, 100),
        )
        
        return {
            "count": result.count,
            "datasets": result.datasets,
            "recommended_mcp": result.recommended_mcp,
            "note": "Use recommended MCP for specialized querying capability"
            if result.recommended_mcp
            else "No specialized MCP recommended; use query_datastore for data access",
        }
    except Exception as e:
        logger.error(f"Error in search_datasets: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def get_dataset_schema(dataset_id: str) -> dict[str, Any]:
    """
    Retrieve the complete schema for any dataset, including field definitions and available resources.
    
    Args:
        dataset_id: The unique identifier of the dataset
    
    Returns:
        Dictionary containing the dataset schema and metadata
    """
    try:
        schema = api_client.get_dataset_schema(dataset_id)
        return {
            "schema": schema,
            "note": "Use resource URLs with specialized MCPs or query_datastore",
        }
    except Exception as e:
        logger.error(f"Error in get_dataset_schema: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def list_organizations(filter_text: str | None = None) -> dict[str, Any]:
    """
    Browse infrastructure organizations and departments.
    
    Args:
        filter_text: Optional text to filter organizations (e.g., 'environment', 'transport')
    
    Returns:
        Dictionary containing the count and list of organizations
    """
    try:
        organizations = api_client.list_organizations(filter_text=filter_text)
        return {
            "count": len(organizations),
            "organizations": organizations,
        }
    except Exception as e:
        logger.error(f"Error in list_organizations: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def browse_by_topic(topic: str) -> dict[str, Any]:
    """
    Explore datasets by subject area.
    
    Args:
        topic: The topic/subject area to browse (e.g., 'environment', 'health', 'transportation', 'water')
    
    Returns:
        Dictionary containing datasets matching the topic with count and dataset details
    """
    try:
        result = api_client.browse_by_topic(topic)
        return result
    except Exception as e:
        logger.error(f"Error in browse_by_topic: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def check_available_mcps() -> dict[str, Any]:
    """
    Check which domain-specific MCPs are available and their status.
    
    Returns:
        Dictionary containing status of core and specialized MCPs
    """
    mcps = {
        "climate-mcp": {
            "name": "Climate & Environment MCP",
            "available": False,
            "capabilities": ["climate data", "emissions", "environmental monitoring"],
        },
        "health-mcp": {
            "name": "Health & Medicine MCP",
            "available": False,
            "capabilities": ["health statistics", "disease data", "medical research"],
        },
        "transportation-mcp": {
            "name": "Transportation MCP",
            "available": False,
            "capabilities": ["traffic data", "road networks", "transit systems"],
        },
        "economic-mcp": {
            "name": "Economic Data MCP",
            "available": False,
            "capabilities": ["economic indicators", "trade data", "business statistics"],
        },
    }
    
    return {
        "core_mcp": {
            "name": "Government Infrastructure MCP (Core)",
            "available": True,
            "version": "0.1.0",
        },
        "specialized_mcps": mcps,
        "note": "Specialized MCPs would be installed separately for domain-specific features",
    }


@mcp.tool()
def get_activity_stream(
    organization: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    See what datasets have been updated recently.
    
    Args:
        organization: Optional filter by organization name
        limit: Maximum number of updates to return (default 20)
    
    Returns:
        Dictionary containing recent dataset updates
    """
    try:
        updates = api_client.get_activity_stream(
            organization=organization,
            limit=limit,
        )
        
        return {
            "count": len(updates),
            "updates": [
                {
                    "dataset_id": u.dataset_id,
                    "dataset_title": u.dataset_title,
                    "organization": u.organization,
                    "timestamp": u.timestamp,
                    "action": u.action,
                }
                for u in updates
            ],
        }
    except Exception as e:
        logger.error(f"Error in get_activity_stream: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def query_datastore(
    resource_id: str,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Query data from a specific resource when specialized MCP not available.
    
    Args:
        resource_id: The resource identifier to query
        filters: Optional filters for the query (e.g., {'field': 'value'})
        limit: Maximum records to return (default 100, max 1000)
    
    Returns:
        Dictionary containing query results and metadata
    """
    try:
        result = api_client.basic_datastore_query(
            resource_id=resource_id,
            filters=filters,
            limit=min(limit, 1000),
        )
        
        return {
            **result,
            "note": "This is basic querying; consider using specialized MCPs for advanced analysis",
        }
    except Exception as e:
        logger.error(f"Error in query_datastore: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """Entry point for the MCP server."""
    if _args.sse:
        import contextlib
        import uvicorn
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware

        logger.info(f"Starting GOV CA DATASET MCP Server on http://{_args.host}:{_args.port}")
        logger.info(f"Streamable HTTP endpoint: http://{_args.host}:{_args.port}/mcp")
        logger.info(f"Legacy SSE endpoint:      http://{_args.host}:{_args.port}/sse")

        sse_app = mcp.sse_app()
        http_app = mcp.streamable_http_app()

        @contextlib.asynccontextmanager
        async def lifespan(app):
            async with contextlib.AsyncExitStack() as stack:
                await stack.enter_async_context(sse_app.router.lifespan_context(app))
                await stack.enter_async_context(http_app.router.lifespan_context(app))
                yield

        app = Starlette(
            routes=sse_app.routes + http_app.routes,
            lifespan=lifespan,
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                    expose_headers=["mcp-session-id"],
                )
            ],
        )

        uvicorn.run(app, host=_args.host, port=_args.port)
    else:
        logger.info("Starting GOV CA DATASET MCP Server with stdio transport...")
        mcp.run()


if __name__ == "__main__":
    main()
