"""
GOV CA TRANSPORTATION INFRASTRUCTURE MCP Server
Specialized MCP for Canadian transportation infrastructure data including
bridges, tunnels, transit, cycling, roads, ports, airports, and railways.
"""
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from gov_ca_transportation.api_client import TransportationAPIClient
from gov_ca_transportation.http_client import RetryConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the MCP server using FastMCP
mcp = FastMCP(
    "gov_ca_transportation",
    instructions="GOV CA TRANSPORTATION INFRASTRUCTURE MCP - Specialized MCP for Canadian transportation infrastructure including bridges, tunnels, transit, cycling, roads, ports, airports, and railways."
)

# Initialize API client
api_client = TransportationAPIClient(retry_config=RetryConfig(max_retries=3))


@mcp.tool()
def query_bridges(
    province: str | None = None,
    city: str | None = None,
    condition: str | None = None,
    capacity_min: float | None = None,
    built_after: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Search and filter bridge infrastructure.
    
    Args:
        province: Filter by province (e.g., 'Ontario', 'British Columbia', 'Alberta')
        city: Filter by city name
        condition: Filter by condition rating (good, fair, poor, critical)
        capacity_min: Minimum capacity in tonnes
        built_after: Filter bridges built after this year
        limit: Maximum records to return (default 100)
    
    Returns:
        Bridge records with GeoJSON and metadata
    """
    try:
        result = api_client.query_bridges(
            province=province,
            city=city,
            condition=condition,
            capacity_min=capacity_min,
            built_after=built_after,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in query_bridges: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def query_tunnels(
    province: str | None = None,
    city: str | None = None,
    length_min: float | None = None,
    tunnel_type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Search and filter tunnel infrastructure.
    
    Args:
        province: Filter by province
        city: Filter by city
        length_min: Minimum length in meters
        tunnel_type: Type of tunnel (road, rail, pedestrian, utility)
        limit: Maximum records to return (default 100)
    
    Returns:
        Tunnel records with GeoJSON and metadata
    """
    try:
        result = api_client.query_tunnels(
            province=province,
            city=city,
            length_min=length_min,
            tunnel_type=tunnel_type,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in query_tunnels: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def query_ports_airports(
    facility_type: str,
    province: str | None = None,
    capacity: str | None = None,
    services: list[str] | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Query ports, marinas, and airports.
    
    Args:
        facility_type: Type of facility - 'port', 'marina', 'airport', or 'heliport' (required)
        province: Filter by province
        capacity: Capacity filter (e.g., 'large', 'medium', 'small')
        services: List of required services (e.g., ['fuel', 'customs', 'repair'])
        limit: Maximum records to return (default 100)
    
    Returns:
        Port/Airport records with GeoJSON and metadata
    """
    try:
        result = api_client.query_ports_airports(
            facility_type=facility_type,
            province=province,
            capacity=capacity,
            services=services,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in query_ports_airports: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def query_railways(
    operator: str | None = None,
    region: str | None = None,
    rail_type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Query railway lines and stations.
    
    Args:
        operator: Railway operator (e.g., 'CN', 'CP', 'VIA Rail')
        region: Region/province filter
        rail_type: Type of railway (freight, passenger, commuter, industrial)
        limit: Maximum records to return (default 100)
    
    Returns:
        Railway infrastructure with GeoJSON
    """
    try:
        result = api_client.query_railways(
            operator=operator,
            region=region,
            rail_type=rail_type,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in query_railways: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def analyze_bridge_conditions(
    region: str,
    group_by: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Aggregate bridge condition data for analysis.
    
    Args:
        region: Region/province to analyze (required)
        group_by: Group results by field (city, structure_type, age, condition)
        limit: Maximum records to return (default 100)
    
    Returns:
        Statistical analysis of bridge conditions
    """
    try:
        result = api_client.analyze_bridge_conditions(
            region=region,
            group_by=group_by,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in analyze_bridge_conditions: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def get_infrastructure_costs(
    infrastructure_type: str,
    location: str,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get actual infrastructure replacement cost data from Statistics Canada.
    Downloads and analyzes the Core Public Infrastructure Survey to provide
    detailed cost breakdowns by condition rating and owner type.
    
    Args:
        infrastructure_type: Type of infrastructure - 'bridge', 'road', or 'transit'
        location: Province name (e.g., 'Ontario', 'Quebec', 'British Columbia') or 'Canada' for national
        limit: Maximum records for fallback search (default 50)
    
    Returns:
        Detailed cost analysis including:
        - Total replacement value (in millions CAD)
        - Costs by condition (Good, Fair, Poor, Very Poor)
        - Costs by owner type (Provincial, Municipal, etc.)
        - Priority investment needed (Poor + Very Poor assets)
        - Data source and quality indicators
    """
    try:
        result = api_client.get_infrastructure_costs(
            infrastructure_type=infrastructure_type,
            location=location,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in get_infrastructure_costs: {e}", exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def compare_across_regions(
    infrastructure_type: str,
    regions: list[str],
    metrics: list[str],
    limit: int = 50,
) -> dict[str, Any]:
    """
    Compare infrastructure across multiple regions.
    
    Args:
        infrastructure_type: Type of infrastructure to compare (bridge, transit, railway, cycling)
        regions: List of regions to compare (e.g., ['Ontario', 'British Columbia', 'Quebec'])
        metrics: List of metrics to compare (e.g., ['count', 'condition', 'age', 'capacity'])
        limit: Maximum records per region (default 50)
    
    Returns:
        Comparative analysis data across regions
    """
    try:
        result = api_client.compare_across_regions(
            infrastructure_type=infrastructure_type,
            regions=regions,
            metrics=metrics,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Error in compare_across_regions: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """Entry point for the Transportation MCP server."""
    logger.info("Starting GOV CA TRANSPORTATION INFRASTRUCTURE MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
