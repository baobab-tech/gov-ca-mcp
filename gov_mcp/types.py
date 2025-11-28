"""
Type definitions for Open Government Canada API responses.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Resource:
    """Represents a dataset resource (file/API)."""
    id: str
    name: str
    description: str
    format: str
    url: str
    size: Optional[int] = None
    last_modified: Optional[str] = None


@dataclass
class Organization:
    """Represents a government organization."""
    id: str
    name: str
    title: str


@dataclass
class Dataset:
    """Represents a dataset in Open Government Canada."""
    id: str
    name: str
    title: str
    notes: str
    organization: Organization
    license_id: str
    tags: List[str]
    resources: List[Resource]
    url: str
    metadata_created: Optional[str] = None
    metadata_modified: Optional[str] = None


@dataclass
class DatasetMetadata:
    """Simplified dataset metadata."""
    id: str
    title: str
    description: str
    organization: str
    tags: List[str]
    resource_count: int
    resources: List[Dict[str, Any]]
    url: str


@dataclass
class SearchResult:
    """Search results from dataset search."""
    count: int
    datasets: List[Dict[str, Any]]
    recommended_mcp: Optional[str] = None


@dataclass
class ActivityUpdate:
    """Recent dataset activity/update."""
    dataset_id: str
    dataset_title: str
    organization: str
    timestamp: str
    action: str  # 'created' or 'modified'


@dataclass
class MCPStatus:
    """Status of specialized MCP servers."""
    name: str
    available: bool
    version: Optional[str] = None
    capabilities: List[str] = None
