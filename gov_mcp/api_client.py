"""
Client for Open Government Canada API.
Handles dataset discovery, search, metadata retrieval, and activity streams.
"""
import logging
from typing import List, Dict, Any, Optional

from gov_mcp.http_client import HTTPClient, RetryConfig
from gov_mcp.types import (
    Dataset,
    DatasetMetadata,
    SearchResult,
    ActivityUpdate,
    Organization,
    Resource,
)

logger = logging.getLogger(__name__)


class OpenGovCanadaClient:
    """Client for Canada's Open Government portal (CKAN-based)."""

    BASE_URL = "https://open.canada.ca/data/api"

    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        Initialize the Open Government Canada API client.
        
        Args:
            retry_config: Retry configuration for HTTP requests
        """
        self.client = HTTPClient(self.BASE_URL, retry_config or RetryConfig())

    def search_all_infrastructure(
        self,
        query: str,
        resource_format: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        organization: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResult:
        """
        Search across all infrastructure datasets in Canada.
        
        Args:
            query: Search query string
            resource_format: Optional filter by resource format (CSV, JSON, XML, PDF, HTML, XLSX, GeoJSON, SHP, KML, etc.)
            jurisdiction: Optional filter by jurisdiction (federal, provincial, municipal)
            organization: Optional filter by organization/department name
            limit: Maximum number of results (default 10)
            offset: Pagination offset (default 0)
            
        Returns:
            SearchResult with matching datasets and recommended MCP
        """
        params: Dict[str, Any] = {
            "q": query,
            "rows": limit,
            "start": offset,
        }
        
        # Build filter query (fq) for CKAN
        filters = []
        if resource_format:
            # res_format filters by resource format (CSV, JSON, XML, PDF, etc.)
            filters.append(f'res_format:{resource_format.upper()}')
        if jurisdiction:
            # jurisdiction can be: federal, provincial, municipal
            filters.append(f'jurisdiction:{jurisdiction.lower()}')
        if organization:
            # Filter by organization name
            filters.append(f'organization:"{organization}"')
        
        if filters:
            params["fq"] = " AND ".join(filters)
        
        try:
            response = self.client.get("3/action/package_search", params=params)
            result = response.get("result", {})
            # Note: package_search returns 'results', not 'records'
            datasets = result.get("results", [])
            
            # Determine recommended MCP based on dataset types
            recommended_mcp = self._determine_mcp(datasets)
            
            return SearchResult(
                count=result.get("count", 0),
                datasets=[
                    {
                        "id": d.get("id"),
                        "title": d.get("title"),
                        "organization": d.get("organization", {}).get("title", "Unknown"),
                        "jurisdiction": d.get("jurisdiction", "unknown"),
                        "description": d.get("notes", "")[:200] if d.get("notes") else "",
                        "formats": list(set(r.get("format", "").upper() for r in d.get("resources", []) if r.get("format"))),
                        "resource_count": len(d.get("resources", [])),
                    }
                    for d in datasets
                ],
                recommended_mcp=recommended_mcp,
            )
        except Exception as e:
            logger.error(f"Error searching infrastructure datasets: {e}")
            raise

    def get_dataset_schema(self, dataset_id: str) -> Dict[str, Any]:
        """
        Retrieve the schema for any dataset.
        
        Args:
            dataset_id: The unique dataset identifier
            
        Returns:
            Complete schema with field definitions
        """
        try:
            response = self.client.get(
                "3/action/package_show",
                params={"id": dataset_id}
            )
            dataset = response.get("result", {})
            
            # Extract resources and their formats
            resources = dataset.get("resources", [])
            schema = {
                "dataset_id": dataset.get("id"),
                "title": dataset.get("title"),
                "description": dataset.get("notes"),
                "organization": dataset.get("organization", {}).get("title"),
                "resources": [
                    {
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "format": r.get("format"),
                        "url": r.get("url"),
                        "description": r.get("description"),
                    }
                    for r in resources
                ],
            }
            return schema
        except Exception as e:
            logger.error(f"Error retrieving dataset schema: {e}")
            raise

    def list_organizations(self, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Browse infrastructure by department/organization.
        
        Args:
            filter_text: Optional text to filter organizations
            
        Returns:
            List of government organizations
        """
        try:
            response = self.client.get(
                "3/action/organization_list",
                params={"all_fields": True}
            )
            organizations = response.get("result", [])
            
            if filter_text:
                organizations = [
                    org for org in organizations
                    if filter_text.lower() in org.get("title", "").lower()
                    or filter_text.lower() in org.get("name", "").lower()
                ]
            
            return [
                {
                    "id": org.get("id"),
                    "name": org.get("name"),
                    "title": org.get("title"),
                    "packages": org.get("package_count", 0),
                }
                for org in organizations
            ]
        except Exception as e:
            logger.error(f"Error listing organizations: {e}")
            raise

    def browse_by_topic(self, topic: str) -> Dict[str, Any]:
        """
        Explore datasets by subject area.
        
        Args:
            topic: The topic/subject area to browse (e.g., 'environment', 'health', 'transportation')
            
        Returns:
            Datasets grouped by topic
        """
        try:
            # Search for datasets matching the topic in query
            # Note: Canadian Open Data doesn't use tags much, search in title/notes instead
            params = {
                "q": topic,
                "rows": 50,
            }
            response = self.client.get("3/action/package_search", params=params)
            result = response.get("result", {})
            # Note: package_search returns 'results', not 'records'
            datasets = result.get("results", [])
            
            return {
                "topic": topic,
                "count": result.get("count", 0),
                "datasets": [
                    {
                        "id": d.get("id"),
                        "title": d.get("title"),
                        "organization": d.get("organization", {}).get("title"),
                        "subject": d.get("subject", []),
                        "keywords": d.get("keywords", {}).get("en", [])[:5],
                    }
                    for d in datasets
                ],
            }
        except Exception as e:
            logger.error(f"Error browsing by topic: {e}")
            raise

    def get_activity_stream(
        self,
        organization: Optional[str] = None,
        limit: int = 20,
    ) -> List[ActivityUpdate]:
        """
        See what datasets have been updated recently.
        
        Args:
            organization: Optional filter by organization
            limit: Maximum number of updates to return
            
        Returns:
            Recent dataset updates
        """
        try:
            # Note: package_search uses 'rows' not 'limit'
            params: Dict[str, Any] = {
                "rows": limit,
                "sort": "metadata_modified desc",  # Get most recently updated first
            }
            
            endpoint = "3/action/package_search"
            if organization:
                params["fq"] = f'organization:"{organization}"'
            
            response = self.client.get(endpoint, params=params)
            result = response.get("result", {})
            # Note: package_search returns 'results', not 'records'
            datasets = result.get("results", [])
            
            updates = []
            for dataset in datasets:
                updates.append(
                    ActivityUpdate(
                        dataset_id=dataset.get("id"),
                        dataset_title=dataset.get("title"),
                        organization=dataset.get("organization", {}).get("title", "Unknown"),
                        timestamp=dataset.get("metadata_modified", "Unknown"),
                        action="modified",
                    )
                )
            
            return sorted(updates, key=lambda x: x.timestamp, reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Error retrieving activity stream: {e}")
            raise

    def basic_datastore_query(
        self,
        resource_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Query data when specialized MCP not available (fallback mode).
        
        Args:
            resource_id: The resource identifier
            filters: Optional filters for the query
            limit: Maximum number of records to return
            
        Returns:
            Basic query results
        """
        try:
            params: Dict[str, Any] = {
                "resource_id": resource_id,
                "limit": limit,
            }
            
            if filters:
                params["filters"] = filters
            
            response = self.client.get(
                "3/action/datastore_search",
                params=params
            )
            
            result = response.get("result", {})
            return {
                "resource_id": resource_id,
                "records": result.get("records", []),
                "total": result.get("total", 0),
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error querying datastore: {e}")
            raise

    def _determine_mcp(self, datasets: List[Dict[str, Any]]) -> Optional[str]:
        """
        Determine recommended MCP based on dataset characteristics.
        
        Args:
            datasets: List of datasets from search results
            
        Returns:
            Recommended MCP name or None
        """
        if not datasets:
            return None
        
        # Analyze subjects, keywords, and titles to recommend specialized MCPs
        all_terms = set()
        for dataset in datasets:
            # Get subjects
            subjects = [s.lower() for s in dataset.get("subject", [])]
            all_terms.update(subjects)
            
            # Get keywords (English)
            keywords = dataset.get("keywords", {})
            if isinstance(keywords, dict):
                en_keywords = [k.lower() for k in keywords.get("en", [])]
                all_terms.update(en_keywords)
            
            # Also check title for relevant terms
            title = dataset.get("title", "").lower()
            all_terms.add(title)
        
        # Convert to single string for easier matching
        all_text = " ".join(all_terms)
        
        # Simple heuristics for MCP recommendation
        if any(term in all_text for term in ["climate", "environment", "emissions", "nature_and_environment"]):
            return "climate-mcp"
        elif any(term in all_text for term in ["health", "disease", "medical", "health_and_safety"]):
            return "health-mcp"
        elif any(term in all_text for term in ["transportation", "road", "traffic", "transport"]):
            return "transportation-mcp"
        elif any(term in all_text for term in ["economic", "trade", "business", "economics_and_industry"]):
            return "economic-mcp"
        
        return None
