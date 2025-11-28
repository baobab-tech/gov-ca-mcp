"""
Type definitions for transportation infrastructure data.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GeoJSONPoint:
    """GeoJSON Point geometry."""
    type: str = "Point"
    coordinates: list[float] = field(default_factory=list)  # [longitude, latitude]


@dataclass
class GeoJSONLineString:
    """GeoJSON LineString geometry."""
    type: str = "LineString"
    coordinates: list[list[float]] = field(default_factory=list)


@dataclass
class GeoJSONPolygon:
    """GeoJSON Polygon geometry."""
    type: str = "Polygon"
    coordinates: list[list[list[float]]] = field(default_factory=list)


@dataclass
class BridgeRecord:
    """Bridge infrastructure record."""
    id: str
    name: str
    province: str
    city: Optional[str]
    condition: Optional[str]  # good, fair, poor, critical
    capacity_tonnes: Optional[float]
    built_year: Optional[int]
    length_meters: Optional[float]
    width_meters: Optional[float]
    structure_type: Optional[str]
    geometry: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TunnelRecord:
    """Tunnel infrastructure record."""
    id: str
    name: str
    province: str
    city: Optional[str]
    tunnel_type: Optional[str]  # road, rail, pedestrian, utility
    length_meters: Optional[float]
    built_year: Optional[int]
    geometry: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class PortAirportRecord:
    """Port or Airport infrastructure record."""
    id: str
    name: str
    facility_type: str  # port, marina, airport, heliport
    province: str
    city: Optional[str]
    capacity: Optional[str]
    services: list[str] = field(default_factory=list)
    geometry: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RailwayRecord:
    """Railway infrastructure record."""
    id: str
    name: str
    operator: Optional[str]
    rail_type: Optional[str]  # freight, passenger, commuter, industrial
    region: Optional[str]
    geometry: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TransitStopRecord:
    """Transit stop record."""
    id: str
    name: str
    city: str
    route_types: list[str] = field(default_factory=list)  # bus, subway, streetcar, lrt
    accessibility: bool = False
    geometry: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GTFSFeed:
    """GTFS feed data."""
    agency_id: str
    agency_name: str
    routes: list[dict] = field(default_factory=list)
    stops: list[dict] = field(default_factory=list)
    schedules: list[dict] = field(default_factory=list)
    realtime_available: bool = False


@dataclass
class CyclingNetworkRecord:
    """Cycling infrastructure record."""
    id: str
    name: Optional[str]
    municipality: str
    surface_type: Optional[str]  # paved, gravel, mixed
    protected: bool = False
    length_km: Optional[float] = None
    geometry: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ConditionAnalysis:
    """Bridge/infrastructure condition analysis."""
    region: str
    total_count: int
    good_count: int
    fair_count: int
    poor_count: int
    critical_count: int
    average_age_years: Optional[float]
    statistics: dict = field(default_factory=dict)


@dataclass
class CoverageAnalysis:
    """Transit coverage analysis."""
    city: str
    radius_meters: int
    total_stops: int
    population_covered: Optional[int]
    area_covered_km2: Optional[float]
    coverage_percentage: Optional[float]
    statistics: dict = field(default_factory=dict)


@dataclass
class InfrastructureCost:
    """Infrastructure cost estimate."""
    infrastructure_type: str
    location: str
    replacement_cost_cad: Optional[float]
    maintenance_cost_annual_cad: Optional[float]
    last_updated: Optional[str]
    metadata: dict = field(default_factory=dict)


@dataclass
class RegionalComparison:
    """Cross-regional infrastructure comparison."""
    infrastructure_type: str
    regions: list[str]
    metrics: list[str]
    data: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
