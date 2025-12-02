"""
API client for Canadian transportation infrastructure data.
Fetches actual infrastructure records from Open Government Canada datasets.
Parses GeoJSON, CSV, and queries ESRI REST APIs to return structured infrastructure data.
"""
import csv
import io
import json
import logging
import ssl
import urllib.request
from typing import Any, Optional
from urllib.parse import urlencode

from gov_ca_transportation.http_client import HTTPClient, RetryConfig

logger = logging.getLogger(__name__)


class TransportationAPIClient:
    """Client for Canadian transportation infrastructure data."""

    BASE_URL = "https://open.canada.ca/data/api"

    # Known dataset resource URLs for direct data access across Canada
    # Each source includes province/city scope and data format info
    KNOWN_RESOURCES = {
        "bridges": {
            "montreal": {
                "province": "Quebec",
                "city": "Montreal",
                "geojson_url": "https://donnees.montreal.ca/dataset/74143072-dd9a-4309-95b4-da9a81a96d52/resource/81b60248-8e94-4dd2-ad4b-66f22daf8c9b/download/2021-liste-structure-donnees-ouvertes.geojson",
                "name": "Montreal Road Structures 2021",
                "format": "geojson",
            },
            "ontario": {
                "province": "Ontario",
                "city": None,  # Province-wide
                "csv_url": "https://data.ontario.ca/dataset/37a472f6-b7ea-4a41-9d4b-64a0c8e5025a/resource/703cdf01-ff09-4b86-b017-6e8d87b11fd2/download/bridge_condition_open_data_2020_en.csv",
                "name": "Ontario Bridge Conditions 2020",
                "format": "csv",
            },
            "nova_scotia": {
                "province": "Nova Scotia",
                "city": None,
                "csv_url": "https://data.novascotia.ca/api/views/gs26-c3fm/rows.csv?accessType=DOWNLOAD",
                "name": "Nova Scotia Structures Database",
                "format": "csv",
            },
        },
        "railways": {
            "national": {
                "province": None,  # National scope
                "geojson_url": "https://gnb.socrata.com/api/geospatial/v8y5-3vbg?method=export&format=GeoJSON",
                "name": "National Railway Network (NRWN)",
                "format": "geojson",
            },
        },
        "airports": {
            "quebec": {
                "province": "Quebec",
                "geojson_url": "https://www.donneesquebec.ca/recherche/dataset/06b37043-e3d8-46e5-8ffc-759bcc8ccecf/resource/51f16d10-e7ed-4d38-848e-c68a75c0d5fd/download/lieux-aerodrome.geojson",
                "name": "Quebec Airports and Aerodromes",
                "format": "geojson",
            },
        },
        "roads": {
            "ontario": {
                "province": "Ontario",
                "city": None,
                "csv_url": "https://files.ontario.ca/opendata/mto_pavement_condition_indices_2014.csv",
                "name": "Ontario Pavement Condition Indices",
                "format": "csv",
                "columns": {
                    "highway": "Highway",
                    "direction": "DIR",
                    "pci": "PCI",  # Pavement Condition Index
                    "dmi": "DMI",  # Distress Manifestation Index
                    "iri": "IRI",  # International Roughness Index
                    "pave_type": "Pave_Type",
                    "latitude": "Latitude",
                    "longitude": "Longitude",
                    "from_km": "FROM_Distance",
                    "to_km": "TO_Distance",
                    "section_from": "Pavement_Section_From",
                    "section_to": "Pavement_Section_To",
                    "func_class": "FUNC_CLASS",
                },
            },
        },
    }

    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.client = HTTPClient(self.BASE_URL, retry_config or RetryConfig())
        # SSL context for fetching data (some gov sites have cert issues)
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def _fetch_geojson(self, url: str) -> dict[str, Any]:
        """Fetch and parse GeoJSON data from a URL."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GovMCP/1.0)"})
            with urllib.request.urlopen(req, timeout=30, context=self._ssl_ctx) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error fetching GeoJSON from {url}: {e}")
            raise

    def _fetch_csv(self, url: str) -> list[dict[str, Any]]:
        """Fetch and parse CSV data from a URL."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GovMCP/1.0)"})
            with urllib.request.urlopen(req, timeout=30, context=self._ssl_ctx) as response:
                data = response.read().decode("utf-8")
                reader = csv.DictReader(io.StringIO(data))
                return list(reader)
        except Exception as e:
            logger.error(f"Error fetching CSV from {url}: {e}")
            raise

    def _query_esri_rest(self, url: str, where: str = "1=1", limit: int = 100) -> dict[str, Any]:
        """Query an ArcGIS/ESRI REST API endpoint."""
        try:
            params = {
                "where": where,
                "outFields": "*",
                "returnGeometry": "true",
                "f": "geojson",
                "resultRecordCount": limit,
            }
            full_url = f"{url}?{urlencode(params)}"
            req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0 (compatible; GovMCP/1.0)"})
            with urllib.request.urlopen(req, timeout=30, context=self._ssl_ctx) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error querying ESRI REST at {url}: {e}")
            raise

    def _extract_coordinates(self, geometry: dict) -> dict[str, Any]:
        """Extract centroid or representative coordinates from GeoJSON geometry."""
        geom_type = geometry.get("type", "")
        coords = geometry.get("coordinates", [])
        
        if geom_type == "Point":
            return {"longitude": coords[0], "latitude": coords[1]} if len(coords) >= 2 else {}
        elif geom_type == "LineString" and coords:
            mid = len(coords) // 2
            return {"longitude": coords[mid][0], "latitude": coords[mid][1]}
        elif geom_type == "Polygon" and coords and coords[0]:
            ring = coords[0]
            avg_lon = sum(p[0] for p in ring) / len(ring)
            avg_lat = sum(p[1] for p in ring) / len(ring)
            return {"longitude": avg_lon, "latitude": avg_lat}
        elif geom_type == "MultiPolygon" and coords and coords[0] and coords[0][0]:
            ring = coords[0][0]
            avg_lon = sum(p[0] for p in ring) / len(ring)
            avg_lat = sum(p[1] for p in ring) / len(ring)
            return {"longitude": avg_lon, "latitude": avg_lat}
        elif geom_type == "MultiLineString" and coords and coords[0]:
            line = coords[0]
            mid = len(line) // 2
            return {"longitude": line[mid][0], "latitude": line[mid][1]}
        return {}

    def _map_condition(self, condition_index: Any) -> str:
        """Map numeric condition index to rating."""
        if condition_index is None:
            return "unknown"
        try:
            idx = float(condition_index)
            if idx >= 80:
                return "good"
            elif idx >= 60:
                return "fair"
            elif idx >= 40:
                return "poor"
            else:
                return "critical"
        except (ValueError, TypeError):
            return str(condition_index) if condition_index else "unknown"

    def _search_datasets(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Search for transportation datasets."""
        params = {
            "q": query,
            "rows": limit,
        }
        
        if filters:
            fq_parts = []
            for key, value in filters.items():
                if value:
                    fq_parts.append(f'{key}:"{value}"')
            if fq_parts:
                params["fq"] = " AND ".join(fq_parts)
        
        try:
            response = self.client.get("3/action/package_search", params=params)
            return response.get("result", {})
        except Exception as e:
            logger.error(f"Error searching datasets: {e}")
            return {"results": [], "count": 0}

    def _query_datastore(
        self,
        resource_id: str,
        filters: Optional[dict] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Query datastore for a specific resource."""
        params = {
            "resource_id": resource_id,
            "limit": limit,
        }
        
        if filters:
            params["filters"] = filters
        
        try:
            response = self.client.get("3/action/datastore_search", params=params)
            return response.get("result", {})
        except Exception as e:
            logger.error(f"Error querying datastore: {e}")
            return {"records": [], "total": 0}

    def query_bridges(
        self,
        province: Optional[str] = None,
        city: Optional[str] = None,
        condition: Optional[str] = None,
        capacity_min: Optional[float] = None,
        built_after: Optional[int] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Search and filter bridge infrastructure across Canada.
        Uses Statistics Canada Core Public Infrastructure data for all provinces,
        supplemented by detailed provincial/municipal data where available.
        
        Args:
            province: Filter by province (e.g., 'Ontario', 'British Columbia', 'Saskatchewan')
            city: Filter by city name (for detailed data where available)
            condition: Filter by condition rating (good, fair, poor, critical)
            capacity_min: Minimum capacity in tonnes (not available in StatCan data)
            built_after: Filter bridges built after this year (for detailed data only)
            limit: Maximum records to return (default 100)
        
        Returns:
            Bridge records with condition data from Statistics Canada,
            plus detailed records from provincial sources where available.
        """
        # Normalize province name
        province_normalized = self.PROVINCE_NAMES.get(province.lower(), province) if province else None
        
        result = {
            "province": province_normalized,
            "city": city,
            "bridges": [],
            "condition_summary": None,
            "sources": [],
            "filters_applied": {
                "province": province,
                "city": city,
                "condition": condition,
                "capacity_min": capacity_min,
                "built_after": built_after,
            },
        }
        
        # First, get StatCan aggregate data for the province/region
        try:
            statcan_data = self._fetch_statcan_bridge_inventory(province_normalized or "Canada")
            if statcan_data:
                result["condition_summary"] = statcan_data.get("condition_distribution")
                result["statcan_data"] = {
                    "source": "Statistics Canada - Core Public Infrastructure Survey",
                    "table_id": self.STATCAN_BRIDGE_INVENTORY["table_id"],
                    "reference_year": statcan_data.get("reference_year", "2022"),
                    "condition_distribution": statcan_data.get("condition_distribution"),
                    "by_owner": statcan_data.get("by_owner"),
                }
                result["sources"].append("Statistics Canada CCPI Survey")
        except Exception as e:
            logger.warning(f"Could not fetch StatCan bridge data: {e}")
        
        # Then, try to get detailed bridge records from provincial/municipal sources
        detailed_bridges = self._fetch_detailed_bridge_records(
            province, city, condition, built_after, limit
        )
        
        result["bridges"] = detailed_bridges.get("bridges", [])
        result["count"] = len(result["bridges"])
        result["sources"].extend(detailed_bridges.get("sources", []))
        
        # Add note about data availability
        if not result["bridges"] and result.get("statcan_data"):
            result["note"] = (
                f"Detailed bridge records not available for {province_normalized or 'all provinces'}. "
                "StatCan aggregate condition data is provided. "
                "Detailed records available for: Ontario, Quebec/Montreal, Nova Scotia."
            )
        
        return result

    def _fetch_statcan_bridge_inventory(self, location: str) -> dict[str, Any]:
        """
        Fetch bridge inventory/condition distribution from Statistics Canada.
        Returns percentage distribution by condition for the specified province.
        """
        import zipfile
        import tempfile
        import os
        
        try:
            zip_url = self.STATCAN_BRIDGE_INVENTORY["url"]
            asset_filter = self.STATCAN_BRIDGE_INVENTORY["asset_filter"]
            
            logger.info(f"Downloading StatCan bridge inventory from {zip_url}")
            
            req = urllib.request.Request(
                zip_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; GovMCP/1.0)"}
            )
            
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=60) as response:
                zip_data = response.read()
            
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "data.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_data)
                
                with zipfile.ZipFile(zip_path, "r") as zf:
                    csv_files = [n for n in zf.namelist() if n.endswith(".csv") and "metadata" not in n.lower()]
                    if not csv_files:
                        return {}
                    
                    with zf.open(csv_files[0]) as csvfile:
                        content = csvfile.read().decode("utf-8-sig")
                        return self._parse_statcan_bridge_inventory_csv(content, asset_filter, location)
            
        except Exception as e:
            logger.error(f"Error fetching StatCan bridge inventory: {e}")
            return {}

    def _parse_statcan_bridge_inventory_csv(
        self,
        csv_content: str,
        asset_filter: str,
        location: str,
    ) -> dict[str, Any]:
        """
        Parse Statistics Canada bridge inventory CSV.
        Returns condition distribution percentages by province.
        """
        result = {
            "reference_year": "2022",
            "condition_distribution": {},
            "by_owner": {},
        }
        
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Condition mapping
        conditions = {
            "Very poor": "very_poor",
            "Poor": "poor", 
            "Fair": "fair",
            "Good": "good",
            "Very good": "very_good",
            "Physical condition unknown": "unknown",
        }
        
        for row in reader:
            geo = row.get("GEO", "")
            asset_type = row.get("Core public infrastructure assets", "")
            owner = row.get("Public organizations", "")
            condition = row.get("Overall physical condition of assets", "")
            value_str = row.get("VALUE", "")
            
            # Filter for bridges and location
            if asset_filter.lower() not in asset_type.lower():
                continue
            if location.lower() not in geo.lower():
                continue
            
            # Parse percentage value
            try:
                value = float(value_str) if value_str and value_str.strip() else 0
            except ValueError:
                continue
            
            # Get reference year
            ref_period = row.get("REF_DATE", "")
            if ref_period:
                result["reference_year"] = ref_period
            
            # Store condition distribution for "All public organizations"
            if "All public organizations" in owner:
                cond_key = conditions.get(condition)
                if cond_key:
                    result["condition_distribution"][cond_key] = {
                        "percentage": value,
                        "label": condition,
                    }
            
            # Store by owner type (for all conditions - look for total)
            # We'll aggregate later or just capture key owner types
            if condition == "Very poor" or condition == "Poor":
                owner_key = owner.lower().replace(" ", "_").replace(",", "")
                if owner_key not in result["by_owner"]:
                    result["by_owner"][owner_key] = {"poor_and_very_poor": 0}
                # This is simplified - in reality we'd need more passes
        
        return result

    def _fetch_detailed_bridge_records(
        self,
        province: Optional[str],
        city: Optional[str],
        condition: Optional[str],
        built_after: Optional[int],
        limit: int,
    ) -> dict[str, Any]:
        """
        Fetch detailed bridge records from provincial/municipal open data sources.
        This supplements the StatCan aggregate data with individual bridge records.
        """
        bridges = []
        sources_queried = []
        
        # Normalize province/city for matching
        prov_lower = province.lower() if province else None
        city_lower = city.lower() if city else None
        
        # Determine which sources to query based on filters
        sources_to_query = []
        for key, resource in self.KNOWN_RESOURCES.get("bridges", {}).items():
            res_province = (resource.get("province") or "").lower()
            res_city = (resource.get("city") or "").lower()
            
            # If no filters, query all sources
            if not province and not city:
                sources_to_query.append((key, resource))
            # If province matches
            elif prov_lower and prov_lower in res_province.lower():
                sources_to_query.append((key, resource))
            # If city matches
            elif city_lower and city_lower in res_city.lower():
                sources_to_query.append((key, resource))
            # Province abbreviation matching
            elif prov_lower in ["qc", "québec"] and "quebec" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["on"] and "ontario" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["ns"] and "nova scotia" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["sk"] and "saskatchewan" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["ab"] and "alberta" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["bc"] and "british columbia" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["mb"] and "manitoba" in res_province:
                sources_to_query.append((key, resource))
        
        # Calculate per-source limit
        num_sources = len(sources_to_query)
        if num_sources > 0 and not province and not city:
            per_source_limit = max(limit // num_sources, 10)
        else:
            per_source_limit = limit
        
        # Query each applicable source
        for key, resource in sources_to_query:
            if len(bridges) >= limit:
                break
            
            remaining = limit - len(bridges)
            source_limit = min(per_source_limit, remaining)
                
            try:
                data_format = resource.get("format", "").lower()
                
                if data_format == "geojson" and resource.get("geojson_url"):
                    bridges.extend(self._parse_bridge_geojson(
                        resource, condition, built_after, source_limit
                    ))
                    sources_queried.append(resource["name"])
                    
                elif data_format == "csv" and resource.get("csv_url"):
                    bridges.extend(self._parse_bridge_csv(
                        resource, city, condition, built_after, source_limit
                    ))
                    sources_queried.append(resource["name"])
                    
            except Exception as e:
                logger.warning(f"Could not fetch data from {resource.get('name')}: {e}")
        
        return {
            "bridges": bridges[:limit],
            "sources": list(set(sources_queried)),
        }

    def _parse_bridge_geojson(
        self, 
        resource: dict, 
        condition: Optional[str], 
        built_after: Optional[int],
        limit: int
    ) -> list[dict]:
        """Parse bridge data from GeoJSON source (e.g., Montreal)."""
        bridges = []
        geojson = self._fetch_geojson(resource["geojson_url"])
        res_city = resource.get("city", "")
        res_province = resource.get("province", "")
        
        for feature in geojson.get("features", []):
            if len(bridges) >= limit:
                break
                
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = self._extract_coordinates(geom)
            
            # Handle Montreal-specific French field names
            if "montreal" in resource.get("name", "").lower():
                structure_type = props.get("Type structure", "")
                bridge_types = ["pont", "bridge", "viaduc", "passerelle", "footbridge"]
                if not any(bt in structure_type.lower() for bt in bridge_types):
                    continue
                
                icg = props.get("ICG")
                condition_rating = self._map_condition(icg)
                if condition and condition.lower() != condition_rating:
                    continue
                
                year_built = props.get("Année de construction")
                if built_after and year_built:
                    try:
                        if int(year_built) < built_after:
                            continue
                    except (ValueError, TypeError):
                        pass
                
                bridges.append({
                    "id": props.get("No structure") or props.get("IDE_STRCT"),
                    "name": props.get("Nom route") or props.get("Nom obstacle"),
                    "structure_type": structure_type,
                    "owner": props.get("Responsablilté de gestion"),
                    "condition_index": icg,
                    "condition_rating": condition_rating,
                    "condition_category": props.get("Catégorie ICG"),
                    "year_built": year_built,
                    "deck_area_m2": props.get("Superficie du tablier"),
                    "location": {
                        "city": res_city,
                        "province": res_province,
                        "coordinates": coords,
                    },
                    "geometry": geom,
                    "source": resource["name"],
                })
            else:
                # Generic GeoJSON parsing
                bridges.append({
                    "id": props.get("id") or props.get("ID"),
                    "name": props.get("name") or props.get("NAME") or props.get("nom"),
                    "structure_type": props.get("type") or props.get("TYPE") or "bridge",
                    "condition_rating": props.get("condition"),
                    "location": {
                        "city": res_city,
                        "province": res_province,
                        "coordinates": coords,
                    },
                    "properties": props,
                    "geometry": geom,
                    "source": resource["name"],
                })
        
        return bridges

    def _parse_bridge_csv(
        self,
        resource: dict,
        city: Optional[str],
        condition: Optional[str],
        built_after: Optional[int],
        limit: int
    ) -> list[dict]:
        """Parse bridge data from CSV source (e.g., Ontario, Nova Scotia)."""
        bridges = []
        csv_data = self._fetch_csv(resource["csv_url"])
        res_province = resource.get("province", "")
        
        for row in csv_data:
            if len(bridges) >= limit:
                break
            
            # Handle Ontario-specific fields
            if "ontario" in resource.get("name", "").lower():
                # Apply city/county filter
                county = row.get("COUNTY", "")
                if city and city.lower() not in county.lower():
                    continue
                
                # Apply condition filter (BCI = Bridge Condition Index)
                bci = row.get("CURRENT BCI")
                condition_rating = self._map_condition_bci(bci)
                if condition and condition.lower() != condition_rating:
                    continue
                
                # Apply built_after filter
                year_built = row.get("YEAR BUILT")
                if built_after and year_built:
                    try:
                        if int(year_built) < built_after:
                            continue
                    except (ValueError, TypeError):
                        pass
                
                lat = row.get("LATITUDE")
                lon = row.get("LONGITUDE")
                coords = {}
                if lat and lon:
                    try:
                        coords = {"latitude": float(lat), "longitude": float(lon)}
                    except (ValueError, TypeError):
                        pass
                
                bridges.append({
                    "id": row.get("ID (SITE N°)"),
                    "name": row.get("STRUCTURE NAME"),
                    "highway": row.get("HIGHWAY NAME"),
                    "structure_type": row.get("TYPE 1") or row.get("CATEGORY"),
                    "category": row.get("CATEGORY"),
                    "subcategory": row.get("SUBCATEGORY 1"),
                    "material": row.get("MATERIAL 1"),
                    "condition_index": bci,
                    "condition_rating": condition_rating,
                    "year_built": year_built,
                    "last_major_rehab": row.get("LAST MAJOR REHAB"),
                    "last_inspection": row.get("LAST INSPECTION DATE"),
                    "span_count": row.get("NUMBER OF SPAN / CELLS"),
                    "length_m": row.get("DECK / CULVERTS LENGTH (m)"),
                    "width_m": row.get("WIDTH TOTAL (m)"),
                    "owner": row.get("OWNER"),
                    "status": row.get("OPERATION STATUS"),
                    "location": {
                        "region": row.get("REGION"),
                        "county": county,
                        "province": res_province,
                        "coordinates": coords,
                    },
                    "source": resource["name"],
                })
                
            elif "nova scotia" in resource.get("name", "").lower():
                # Nova Scotia has simpler fields
                lat = row.get("Latitude")
                lon = row.get("Longitude")
                coords = {}
                if lat and lon:
                    try:
                        coords = {"latitude": float(lat), "longitude": float(lon)}
                    except (ValueError, TypeError):
                        pass
                
                bridges.append({
                    "id": row.get("StructureID"),
                    "name": row.get("StructureName"),
                    "location": {
                        "province": res_province,
                        "coordinates": coords,
                    },
                    "source": resource["name"],
                })
            else:
                # Generic CSV parsing
                bridges.append({
                    "id": row.get("id") or row.get("ID"),
                    "name": row.get("name") or row.get("NAME"),
                    "location": {"province": res_province},
                    "properties": row,
                    "source": resource["name"],
                })
        
        return bridges

    def _map_condition_bci(self, bci_value) -> str:
        """Map Ontario Bridge Condition Index (0-100) to rating."""
        if bci_value is None:
            return "unknown"
        try:
            bci = float(bci_value)
            if bci >= 80:
                return "good"
            elif bci >= 60:
                return "fair"
            elif bci >= 40:
                return "poor"
            else:
                return "critical"
        except (ValueError, TypeError):
            return "unknown"

    def query_road_conditions(
        self,
        province: Optional[str] = None,
        highway: Optional[str] = None,
        condition: Optional[str] = None,
        pci_min: Optional[float] = None,
        pci_max: Optional[float] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Query road/pavement condition data across Canada.
        
        Args:
            province: Filter by province (e.g., 'Ontario'). Currently Ontario has detailed data.
            highway: Filter by highway number/name (e.g., '401', '17')
            condition: Filter by condition rating (good, fair, poor, critical)
            pci_min: Minimum Pavement Condition Index (0-100)
            pci_max: Maximum Pavement Condition Index (0-100)
            limit: Maximum records to return (default 100)
        
        Returns:
            Road condition records with PCI, DMI, IRI metrics and location data
        """
        province_normalized = self.PROVINCE_NAMES.get(province.lower(), province) if province else None
        
        result = {
            "province": province_normalized,
            "roads": [],
            "condition_summary": {
                "good": 0,      # PCI >= 80
                "fair": 0,      # PCI 60-79
                "poor": 0,      # PCI 40-59
                "critical": 0,  # PCI < 40
            },
            "sources": [],
            "filters_applied": {
                "province": province,
                "highway": highway,
                "condition": condition,
                "pci_min": pci_min,
                "pci_max": pci_max,
            },
        }
        
        # Map condition string to PCI range
        condition_to_pci = {
            "good": (80, 100),
            "fair": (60, 79.99),
            "poor": (40, 59.99),
            "critical": (0, 39.99),
        }
        
        if condition and condition.lower() in condition_to_pci:
            range_min, range_max = condition_to_pci[condition.lower()]
            if pci_min is None or pci_min < range_min:
                pci_min = range_min
            if pci_max is None or pci_max > range_max:
                pci_max = range_max
        
        # Query available province data
        query_ontario = (
            province is None or 
            province_normalized == "Ontario" or
            (province and province.lower() in ["ontario", "on"])
        )
        
        if query_ontario:
            try:
                ontario_roads = self._fetch_ontario_road_conditions(
                    highway=highway,
                    pci_min=pci_min,
                    pci_max=pci_max,
                    limit=limit,
                )
                result["roads"].extend(ontario_roads.get("roads", []))
                result["sources"].append(ontario_roads.get("source", "Ontario Pavement Condition Data"))
                
                # Update condition summary
                for road in ontario_roads.get("roads", []):
                    cond = road.get("condition", "").lower()
                    if cond in result["condition_summary"]:
                        result["condition_summary"][cond] += 1
            except Exception as e:
                logger.error(f"Error fetching Ontario road data: {e}")
        
        result["count"] = len(result["roads"])
        
        if not result["roads"]:
            result["note"] = (
                "Detailed road condition data currently available for: Ontario. "
                "Other provinces coming soon. Use get_infrastructure_costs for aggregate road statistics."
            )
        
        return result

    def _fetch_ontario_road_conditions(
        self,
        highway: Optional[str] = None,
        pci_min: Optional[float] = None,
        pci_max: Optional[float] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Fetch Ontario pavement condition data from open data portal.
        
        Returns road sections with PCI (Pavement Condition Index),
        DMI (Distress Manifestation Index), and IRI (International Roughness Index).
        """
        try:
            resource = self.KNOWN_RESOURCES["roads"]["ontario"]
            csv_data = self._fetch_csv(resource["csv_url"])
            
            roads = []
            cols = resource["columns"]
            
            for row in csv_data:
                # Parse PCI value
                pci_str = row.get(cols["pci"], "")
                try:
                    pci = float(pci_str) if pci_str else None
                except ValueError:
                    pci = None
                
                # Skip if PCI filters don't match
                if pci is not None:
                    if pci_min is not None and pci < pci_min:
                        continue
                    if pci_max is not None and pci > pci_max:
                        continue
                
                # Filter by highway if specified
                row_highway = row.get(cols["highway"], "")
                if highway:
                    # Allow partial match (e.g., "401" matches "Highway 401")
                    if str(highway).lower() not in str(row_highway).lower():
                        continue
                
                # Parse other metrics
                try:
                    dmi = float(row.get(cols["dmi"], "")) if row.get(cols["dmi"]) else None
                except ValueError:
                    dmi = None
                
                try:
                    iri = float(row.get(cols["iri"], "")) if row.get(cols["iri"]) else None
                except ValueError:
                    iri = None
                
                try:
                    lat = float(row.get(cols["latitude"], "")) if row.get(cols["latitude"]) else None
                    lon = float(row.get(cols["longitude"], "")) if row.get(cols["longitude"]) else None
                except ValueError:
                    lat, lon = None, None
                
                try:
                    from_km = float(row.get(cols["from_km"], "")) if row.get(cols["from_km"]) else None
                    to_km = float(row.get(cols["to_km"], "")) if row.get(cols["to_km"]) else None
                except ValueError:
                    from_km, to_km = None, None
                
                road_record = {
                    "highway": row_highway,
                    "direction": row.get(cols["direction"], ""),
                    "pci": pci,
                    "condition": self._map_road_condition(pci),
                    "dmi": dmi,
                    "iri": iri,
                    "pavement_type": row.get(cols["pave_type"], ""),
                    "section_from": row.get(cols["section_from"], ""),
                    "section_to": row.get(cols["section_to"], ""),
                    "from_km": from_km,
                    "to_km": to_km,
                    "functional_class": row.get(cols["func_class"], ""),
                    "province": "Ontario",
                }
                
                if lat and lon:
                    road_record["latitude"] = lat
                    road_record["longitude"] = lon
                    road_record["geometry"] = {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                
                roads.append(road_record)
                
                if len(roads) >= limit:
                    break
            
            return {
                "roads": roads,
                "source": resource["name"],
                "count": len(roads),
            }
            
        except Exception as e:
            logger.error(f"Error fetching Ontario road conditions: {e}")
            return {"roads": [], "source": "Ontario Pavement Condition Data", "error": str(e)}

    def _map_road_condition(self, pci: Optional[float]) -> str:
        """Map Pavement Condition Index to condition rating."""
        if pci is None:
            return "unknown"
        if pci >= 80:
            return "good"
        elif pci >= 60:
            return "fair"
        elif pci >= 40:
            return "poor"
        else:
            return "critical"

    def query_tunnels(
        self,
        province: Optional[str] = None,
        city: Optional[str] = None,
        length_min: Optional[float] = None,
        tunnel_type: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Search and filter tunnel infrastructure.
        Returns actual tunnel records with location and metadata.
        """
        tunnels = []
        sources_queried = []
        
        # Montreal road structures include tunnels
        query_montreal = (
            province is None or 
            province.lower() in ["quebec", "québec", "qc"] or
            (city and city.lower() in ["montreal", "montréal"])
        )
        
        if query_montreal:
            try:
                resource = self.KNOWN_RESOURCES["bridges"]["montreal"]
                geojson = self._fetch_geojson(resource["geojson_url"])
                sources_queried.append(resource["name"])
                
                for feature in geojson.get("features", []):
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    coords = self._extract_coordinates(geom)
                    
                    # Montreal uses French field names
                    structure_type = props.get("Type structure", "")
                    
                    # Filter to tunnels only
                    if "tunnel" not in structure_type.lower():
                        continue
                    
                    # Apply tunnel_type filter
                    if tunnel_type and tunnel_type.lower() not in structure_type.lower():
                        continue
                    
                    # Apply length_min filter
                    length = props.get("Superficie du tablier")  # Using deck area as proxy
                    if length_min and length:
                        try:
                            if float(length) < length_min:
                                continue
                        except (ValueError, TypeError):
                            pass
                    
                    tunnel_record = {
                        "id": props.get("No structure") or props.get("IDE_STRCT"),
                        "name": props.get("Nom route") or props.get("Nom obstacle"),
                        "tunnel_type": structure_type,
                        "owner": props.get("Responsablilté de gestion"),
                        "condition_index": props.get("ICG"),
                        "condition_rating": self._map_condition(props.get("ICG")),
                        "condition_category": props.get("Catégorie ICG"),
                        "year_built": props.get("Année de construction"),
                        "deck_area_m2": length,
                        "status": props.get("Statut"),
                        "location": {
                            "city": "Montreal",
                            "province": "Quebec",
                            "coordinates": coords,
                        },
                        "geometry": geom,
                        "source": resource["name"],
                    }
                    tunnels.append(tunnel_record)
                    
                    if len(tunnels) >= limit:
                        break
                        
            except Exception as e:
                logger.warning(f"Could not fetch Montreal tunnel data: {e}")
        
        # Search for additional tunnel datasets
        if len(tunnels) < limit:
            search_query = "tunnel infrastructure"
            if province:
                search_query += f" {province}"
            
            search_results = self._search_datasets(search_query, limit=10)
            
            for ds in search_results.get("results", []):
                if len(tunnels) >= limit:
                    break
                for resource in ds.get("resources", []):
                    fmt = resource.get("format", "").upper()
                    url = resource.get("url", "")
                    
                    if fmt == "GEOJSON" and url:
                        try:
                            geojson = self._fetch_geojson(url)
                            sources_queried.append(ds.get("title", "Unknown"))
                            
                            for feature in geojson.get("features", []):
                                if len(tunnels) >= limit:
                                    break
                                props = feature.get("properties", {})
                                geom = feature.get("geometry", {})
                                coords = self._extract_coordinates(geom)
                                
                                tunnel_record = {
                                    "id": props.get("id") or props.get("ID"),
                                    "name": props.get("name") or props.get("NAME") or props.get("nom"),
                                    "tunnel_type": props.get("type") or "tunnel",
                                    "location": {"coordinates": coords},
                                    "properties": props,
                                    "geometry": geom,
                                    "source": ds.get("title"),
                                }
                                tunnels.append(tunnel_record)
                        except Exception:
                            continue
        
        return {
            "count": len(tunnels),
            "tunnels": tunnels[:limit],
            "sources": list(set(sources_queried)),
            "filters_applied": {
                "province": province,
                "city": city,
                "length_min": length_min,
                "tunnel_type": tunnel_type,
            },
        }

    def query_ports_airports(
        self,
        facility_type: str,
        province: Optional[str] = None,
        capacity: Optional[str] = None,
        services: Optional[list[str]] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Query ports, marinas, and airports.
        Returns actual facility records with location and metadata.
        """
        facilities = []
        sources_queried = []
        
        # Query Quebec airports/aerodromes for airport types
        if facility_type.lower() in ["airport", "aerodrome", "heliport"]:
            try:
                resource = self.KNOWN_RESOURCES["airports"].get("quebec")
                if resource and resource.get("geojson_url"):
                    geojson = self._fetch_geojson(resource["geojson_url"])
                    sources_queried.append(resource["name"])
                    
                    for feature in geojson.get("features", []):
                        if len(facilities) >= limit:
                            break
                        props = feature.get("properties", {})
                        geom = feature.get("geometry", {})
                        coords = self._extract_coordinates(geom)
                        
                        facility = {
                            "id": props.get("id") or props.get("ID") or props.get("code"),
                            "name": props.get("name") or props.get("nom") or props.get("NOM"),
                            "facility_type": props.get("type") or facility_type,
                            "icao_code": props.get("icao") or props.get("ICAO"),
                            "iata_code": props.get("iata") or props.get("IATA"),
                            "location": {
                                "province": "Quebec",
                                "coordinates": coords,
                            },
                            "properties": props,
                            "geometry": geom,
                            "source": resource["name"],
                        }
                        facilities.append(facility)
            except Exception as e:
                logger.warning(f"Could not fetch Quebec airport data: {e}")
        
        # Search for additional datasets via Open Data API
        if len(facilities) < limit:
            search_query = f"{facility_type} infrastructure canada"
            if province:
                search_query += f" {province}"
            
            search_results = self._search_datasets(search_query, limit=10)
            
            for ds in search_results.get("results", []):
                if len(facilities) >= limit:
                    break
                for resource in ds.get("resources", []):
                    fmt = resource.get("format", "").upper()
                    url = resource.get("url", "")
                    
                    if fmt == "GEOJSON" and url:
                        try:
                            geojson = self._fetch_geojson(url)
                            sources_queried.append(ds.get("title", "Unknown"))
                            
                            for feature in geojson.get("features", []):
                                if len(facilities) >= limit:
                                    break
                                props = feature.get("properties", {})
                                geom = feature.get("geometry", {})
                                coords = self._extract_coordinates(geom)
                                
                                facility = {
                                    "id": props.get("id") or props.get("ID"),
                                    "name": props.get("name") or props.get("NAME") or props.get("nom"),
                                    "facility_type": facility_type,
                                    "location": {"coordinates": coords},
                                    "properties": props,
                                    "geometry": geom,
                                    "source": ds.get("title"),
                                }
                                facilities.append(facility)
                        except Exception:
                            continue
        
        return {
            "count": len(facilities),
            "facilities": facilities[:limit],
            "facility_type": facility_type,
            "sources": list(set(sources_queried)),
            "filters_applied": {
                "province": province,
                "capacity": capacity,
                "services": services,
            },
        }

    def query_railways(
        self,
        operator: Optional[str] = None,
        region: Optional[str] = None,
        rail_type: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Query railway lines and stations.
        Returns actual railway records with GeoJSON and metadata.
        """
        railways = []
        sources_queried = []
        
        # Query National Railway Network (NRWN)
        try:
            resource = self.KNOWN_RESOURCES["railways"]["national"]
            geojson = self._fetch_geojson(resource["geojson_url"])
            sources_queried.append(resource["name"])
            
            for feature in geojson.get("features", []):
                if len(railways) >= limit:
                    break
                    
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                coords = self._extract_coordinates(geom)
                
                # NRWN uses specific field names (from NB Socrata export)
                # trackclass, subdi1name, adminarea, trackname, tracknid, crossintyp, roadclass, levelcross
                feat_province = props.get("adminarea") or props.get("PROV_EN") or props.get("province")
                feat_type = props.get("crossintyp") or props.get("RRTYPE_EN") or props.get("type")  # Road, Trail, etc.
                track_class = props.get("trackclass") or props.get("trackclasc")  # Main, Siding, etc.
                
                # Apply region filter
                if region and feat_province:
                    if region.lower() not in feat_province.lower():
                        continue
                
                # Apply rail_type filter (using track class or crossing type)
                if rail_type:
                    if track_class and rail_type.lower() in track_class.lower():
                        pass
                    elif feat_type and rail_type.lower() in feat_type.lower():
                        pass
                    else:
                        continue
                
                railway = {
                    "id": props.get("tracknid") or props.get("nid") or props.get("tcid"),
                    "name": props.get("trackname") or props.get("crosstypnm") or props.get("subdi1name"),  # crossing name or subdivision
                    "subdivision": props.get("subdi1name"),  # e.g., "Sussex"
                    "subdivision_distance": props.get("subd1dist"),  # e.g., 19.57 miles
                    "track_class": track_class,  # e.g., "Main"
                    "crossing_type": feat_type,  # e.g., "Road"
                    "road_class": props.get("roadclass"),  # e.g., "Local/Unknown"
                    "level_crossing": props.get("levelcross"),  # e.g., "Under"
                    "crossing_access": props.get("crosacces"),  # e.g., "Public"
                    "warning_system": props.get("warningsys"),  
                    "location": {
                        "province": feat_province,
                        "coordinates": coords,
                    },
                    "data_provider": props.get("attprovide") or props.get("geoprovide"),  # e.g., "Federal"
                    "geometry": geom,
                    "source": resource["name"],
                }
                railways.append(railway)
                
        except Exception as e:
            logger.warning(f"Could not fetch NRWN data: {e}")
        
        # Search for additional railway datasets
        if len(railways) < limit:
            search_query = "railway rail infrastructure"
            if operator:
                search_query += f" {operator}"
            if region:
                search_query += f" {region}"
            
            search_results = self._search_datasets(search_query, limit=5)
            
            for ds in search_results.get("results", []):
                if len(railways) >= limit:
                    break
                for res in ds.get("resources", []):
                    fmt = res.get("format", "").upper()
                    url = res.get("url", "")
                    
                    if fmt == "GEOJSON" and url:
                        try:
                            geojson = self._fetch_geojson(url)
                            sources_queried.append(ds.get("title", "Unknown"))
                            
                            for feature in geojson.get("features", []):
                                if len(railways) >= limit:
                                    break
                                props = feature.get("properties", {})
                                geom = feature.get("geometry", {})
                                coords = self._extract_coordinates(geom)
                                
                                railway = {
                                    "id": props.get("id") or props.get("ID"),
                                    "name": props.get("name") or props.get("NAME"),
                                    "operator": props.get("operator") or props.get("OPERATOR"),
                                    "rail_type": props.get("type") or props.get("TYPE"),
                                    "location": {"coordinates": coords},
                                    "properties": props,
                                    "geometry": geom,
                                    "source": ds.get("title"),
                                }
                                railways.append(railway)
                        except Exception:
                            continue
        
        return {
            "count": len(railways),
            "railways": railways[:limit],
            "sources": list(set(sources_queried)),
            "filters_applied": {
                "operator": operator,
                "region": region,
                "rail_type": rail_type,
            },
        }

    def analyze_bridge_conditions(
        self,
        region: str,
        group_by: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Aggregate bridge condition data for analysis using Statistics Canada
        Core Public Infrastructure Survey data.
        
        Returns statistical analysis of bridge conditions for any province/territory
        using the unified StatCan approach (Table 34-10-0288-01).
        
        Args:
            region: Province/territory name (e.g., 'Ontario', 'Saskatchewan', 'Canada')
            group_by: Group results by field (owner, condition) - limited by StatCan data
            limit: Maximum detailed records to return (default 100)
        
        Returns:
            Condition distribution percentages from Statistics Canada
        """
        # Normalize province name
        region_normalized = self.PROVINCE_NAMES.get(region.lower(), region) if region else "Canada"
        
        # Use unified query_bridges approach which fetches StatCan data
        bridges_data = self.query_bridges(province=region_normalized, limit=limit)
        
        # Get StatCan aggregate condition data (the primary source)
        statcan_data = bridges_data.get("statcan_data", {})
        condition_dist = statcan_data.get("condition_distribution", {})
        
        if not condition_dist:
            # Try fetching directly if not in bridges_data
            try:
                statcan_data = self._fetch_statcan_bridge_inventory(region_normalized)
                condition_dist = statcan_data.get("condition_distribution", {})
            except Exception as e:
                logger.warning(f"Could not fetch StatCan data for {region_normalized}: {e}")
        
        if not condition_dist:
            return {
                "region": region_normalized,
                "error": "No bridge condition data available for this region",
                "sources": ["Statistics Canada - CCPI Survey"],
                "suggestion": "Try 'Ontario', 'Quebec', 'British Columbia', 'Alberta', 'Saskatchewan', or 'Canada' for available data",
            }
        
        # Build condition summary from StatCan percentages
        condition_summary = {}
        total_percentage = 0
        
        # Map StatCan conditions to our categories
        condition_mapping = {
            "very_good": "very_good",
            "good": "good",
            "fair": "fair",
            "poor": "poor",
            "very_poor": "very_poor",
            "unknown": "unknown",
        }
        
        for key, mapping in condition_mapping.items():
            if key in condition_dist:
                pct = condition_dist[key].get("percentage", 0)
                condition_summary[mapping] = {
                    "percentage": pct,
                    "label": condition_dist[key].get("label", key.replace("_", " ").title()),
                }
                total_percentage += pct
        
        # Calculate combined poor/critical percentage
        poor_pct = condition_summary.get("poor", {}).get("percentage", 0)
        very_poor_pct = condition_summary.get("very_poor", {}).get("percentage", 0)
        needs_attention_pct = poor_pct + very_poor_pct
        
        # Get detailed bridge records if available
        detailed_bridges = bridges_data.get("bridges", [])
        
        # Group by owner if requested and we have StatCan owner data
        grouped_data = {}
        by_owner = statcan_data.get("by_owner", {})
        if group_by == "owner" and by_owner:
            grouped_data = by_owner
        elif group_by == "condition":
            grouped_data = condition_summary
        
        return {
            "region": region_normalized,
            "reference_year": statcan_data.get("reference_year", "2022"),
            "data_source": {
                "name": "Statistics Canada - Core Public Infrastructure Survey",
                "table_id": self.STATCAN_BRIDGE_INVENTORY.get("table_id", "34-10-0288-01"),
                "description": "Physical condition of core public infrastructure assets by province/territory",
            },
            "condition_summary": condition_summary,
            "analysis": {
                "needs_attention_percentage": round(needs_attention_pct, 1),
                "good_or_better_percentage": round(
                    condition_summary.get("good", {}).get("percentage", 0) +
                    condition_summary.get("very_good", {}).get("percentage", 0),
                    1
                ),
                "total_accounted_percentage": round(total_percentage, 1),
            },
            "grouped_by": group_by,
            "groups": grouped_data if grouped_data else None,
            "detailed_records_available": len(detailed_bridges),
            "detailed_records": detailed_bridges[:10] if detailed_bridges else [],  # Sample of detailed records
            "sources": bridges_data.get("sources", ["Statistics Canada CCPI Survey"]),
            "note": (
                f"Condition percentages from Statistics Canada for {region_normalized}. "
                f"Detailed bridge records: {len(detailed_bridges)} available from provincial sources."
            ) if detailed_bridges else (
                f"Condition percentages from Statistics Canada for {region_normalized}. "
                "Detailed bridge records available for: Ontario, Quebec/Montreal, Nova Scotia."
            ),
        }

    # Statistics Canada infrastructure cost data URLs
    STATCAN_COST_DATA = {
        "bridge": {
            "url": "https://www150.statcan.gc.ca/n1/tbl/csv/34100284-eng.zip",
            "table_id": "34-10-0284-01",
            "title": "Estimated replacement value of core public infrastructure assets",
            "asset_filter": "Bridge and tunnel assets",
        },
        "road": {
            "url": "https://www150.statcan.gc.ca/n1/tbl/csv/34100284-eng.zip",
            "table_id": "34-10-0284-01",
            "title": "Estimated replacement value of core public infrastructure assets",
            "asset_filter": "Road assets",
        },
        "transit": {
            "url": "https://www150.statcan.gc.ca/n1/tbl/csv/34100284-eng.zip",
            "table_id": "34-10-0284-01",
            "title": "Estimated replacement value of core public infrastructure assets",
            "asset_filter": "Public transit assets",
        },
    }

    # Statistics Canada bridge inventory/condition distribution data
    STATCAN_BRIDGE_INVENTORY = {
        "url": "https://www150.statcan.gc.ca/n1/tbl/csv/34100288-eng.zip",
        "table_id": "34-10-0288-01",
        "title": "Inventory distribution of core public infrastructure assets by physical condition rating",
        "asset_filter": "Bridge and tunnel assets",
    }

    # Province name mappings for StatCan data
    PROVINCE_NAMES = {
        "ontario": "Ontario",
        "quebec": "Quebec",
        "british columbia": "British Columbia",
        "alberta": "Alberta",
        "manitoba": "Manitoba",
        "saskatchewan": "Saskatchewan",
        "nova scotia": "Nova Scotia",
        "new brunswick": "New Brunswick",
        "newfoundland": "Newfoundland and Labrador",
        "pei": "Prince Edward Island",
        "prince edward island": "Prince Edward Island",
        "yukon": "Yukon",
        "northwest territories": "Northwest Territories",
        "nunavut": "Nunavut",
        "canada": "Canada",
    }

    def get_infrastructure_costs(
        self,
        infrastructure_type: str,
        location: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Get actual cost data for transportation infrastructure from Statistics Canada.
        Downloads and analyzes the Core Public Infrastructure Survey data.
        Returns replacement cost estimates by condition rating and owner type.
        
        Args:
            infrastructure_type: Type of infrastructure (bridge, road, transit)
            location: Province name or 'Canada' for national data
            limit: Maximum records to return (default 50)
        
        Returns:
            Detailed cost breakdown including:
            - Total replacement value
            - Costs by condition (Good, Fair, Poor, Very Poor)
            - Costs by owner type (Provincial, Municipal, etc.)
        """
        infra_lower = infrastructure_type.lower()
        
        # Check if we have StatCan data for this infrastructure type
        if infra_lower not in self.STATCAN_COST_DATA:
            return self._fallback_cost_search(infrastructure_type, location, limit)
        
        statcan_config = self.STATCAN_COST_DATA[infra_lower]
        
        # Normalize location name
        location_normalized = self.PROVINCE_NAMES.get(location.lower(), location)
        
        try:
            # Download and parse StatCan data
            cost_data = self._fetch_statcan_cost_data(
                statcan_config["url"],
                statcan_config["asset_filter"],
                location_normalized,
            )
            
            if not cost_data:
                return self._fallback_cost_search(infrastructure_type, location, limit)
            
            return {
                "infrastructure_type": infrastructure_type,
                "location": location_normalized,
                "source": {
                    "name": "Statistics Canada - Core Public Infrastructure Survey",
                    "table_id": statcan_config["table_id"],
                    "title": statcan_config["title"],
                    "reference_year": cost_data.get("reference_year", "2020"),
                    "url": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={statcan_config['table_id'].replace('-', '')}01",
                },
                "total_replacement_value": cost_data.get("total"),
                "costs_by_condition": cost_data.get("by_condition", {}),
                "costs_by_owner": cost_data.get("by_owner", {}),
                "priority_investment_needed": cost_data.get("priority_investment", {}),
                "unit": "millions CAD",
                "data_quality": "A (Excellent) - Statistics Canada certified",
            }
            
        except Exception as e:
            logger.error(f"Error fetching StatCan cost data: {e}")
            return self._fallback_cost_search(infrastructure_type, location, limit)

    def _fetch_statcan_cost_data(
        self,
        zip_url: str,
        asset_filter: str,
        location: str,
    ) -> dict[str, Any]:
        """
        Download and parse Statistics Canada infrastructure cost CSV from ZIP.
        """
        import zipfile
        import tempfile
        import os
        
        try:
            # Download the ZIP file
            logger.info(f"Downloading StatCan cost data from {zip_url}")
            
            # Create SSL context that doesn't verify (StatCan has cert issues sometimes)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                zip_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; GovMCP/1.0)"}
            )
            
            with urllib.request.urlopen(req, context=ctx, timeout=60) as response:
                zip_data = response.read()
            
            # Extract and parse CSV from ZIP
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "data.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_data)
                
                with zipfile.ZipFile(zip_path, "r") as zf:
                    # Find the main CSV file (not metadata)
                    csv_files = [n for n in zf.namelist() if n.endswith(".csv") and "metadata" not in n.lower()]
                    if not csv_files:
                        logger.error("No CSV file found in ZIP")
                        return {}
                    
                    csv_filename = csv_files[0]
                    with zf.open(csv_filename) as csvfile:
                        # Read and decode CSV content
                        content = csvfile.read().decode("utf-8-sig")
                        return self._parse_statcan_cost_csv(content, asset_filter, location)
            
        except Exception as e:
            logger.error(f"Error downloading/parsing StatCan ZIP: {e}")
            return {}

    def _parse_statcan_cost_csv(
        self,
        csv_content: str,
        asset_filter: str,
        location: str,
    ) -> dict[str, Any]:
        """
        Parse Statistics Canada infrastructure cost CSV and extract relevant data.
        
        CSV columns (from StatCan table 34-10-0284-01):
        - REF_DATE: Reference year
        - GEO: Geography (Canada, province names)
        - Core public infrastructure assets: Asset type
        - Financial value of assets: Measure type (Estimated Replacement Value, etc.)
        - Overall physical condition of assets: Condition rating
        - Public organizations: Owner type
        - VALUE: Dollar amount in millions
        """
        result = {
            "reference_year": "2020",
            "total": None,
            "by_condition": {},
            "by_owner": {},
            "priority_investment": {},
        }
        
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Track values for aggregation
        condition_costs = {"Good": 0, "Fair": 0, "Poor": 0, "Very poor": 0}
        owner_costs = {
            "Provincial and territorial": 0,
            "Municipal (all)": 0,
            "Urban municipalities": 0,
            "Rural municipalities": 0,
            "Local and regional": 0,
        }
        total_all = None
        
        for row in reader:
            # Get values using actual StatCan column names
            geo = row.get("GEO", "")
            asset_type = row.get("Core public infrastructure assets", "")
            measure = row.get("Financial value of assets", "")
            condition = row.get("Overall physical condition of assets", "")
            owner = row.get("Public organizations", "")
            value_str = row.get("VALUE", "")
            
            # Filter for our infrastructure type and location
            if asset_filter.lower() not in asset_type.lower():
                continue
            if location.lower() not in geo.lower():
                continue
            if "Estimated Replacement Value" not in measure:
                continue
            
            # Parse value (in millions)
            try:
                value = float(value_str) if value_str and value_str.strip() else 0
            except ValueError:
                continue
            
            # Get reference year
            ref_period = row.get("REF_DATE", "")
            if ref_period:
                result["reference_year"] = ref_period
            
            # Extract total
            if "All physical conditions" in condition and "All public organizations" in owner:
                total_all = value
            
            # Extract by condition (for all public organizations)
            if "All public organizations" in owner:
                for cond in ["Good", "Fair", "Poor", "Very poor"]:
                    if condition == cond:
                        condition_costs[cond] = value
            
            # Extract by owner (for all conditions)
            if "All physical conditions" in condition:
                if "Provincial and territorial organizations" in owner:
                    owner_costs["Provincial and territorial"] = value
                elif owner == "All municipalities":
                    owner_costs["Municipal (all)"] = value
                elif "All urban municipalities" in owner:
                    owner_costs["Urban municipalities"] = value
                elif "All rural municipalities" in owner:
                    owner_costs["Rural municipalities"] = value
                elif "Local and regional organizations" in owner:
                    owner_costs["Local and regional"] = value
        
        # Build result
        result["total"] = {
            "value": total_all,
            "formatted": f"${total_all:,.1f} million" if total_all else "N/A",
            "in_billions": f"${total_all/1000:.1f} billion" if total_all and total_all > 1000 else None,
        }
        
        # Costs by condition with percentages
        if total_all and total_all > 0:
            for cond, val in condition_costs.items():
                pct = (val / total_all * 100) if val else 0
                result["by_condition"][cond.lower().replace(" ", "_")] = {
                    "value_millions": val,
                    "formatted": f"${val:,.1f} million" if val else "N/A",
                    "percentage": round(pct, 1),
                }
        
        # Costs by owner
        for owner_type, val in owner_costs.items():
            if val > 0:
                result["by_owner"][owner_type.lower().replace(" ", "_").replace("(", "").replace(")", "")] = {
                    "value_millions": val,
                    "formatted": f"${val:,.1f} million" if val else "N/A",
                }
        
        # Priority investment (Poor + Very Poor)
        poor_total = condition_costs.get("Poor", 0) + condition_costs.get("Very poor", 0)
        result["priority_investment"] = {
            "poor_and_very_poor_total": {
                "value_millions": poor_total,
                "formatted": f"${poor_total:,.1f} million",
                "in_billions": f"${poor_total/1000:.2f} billion" if poor_total > 500 else None,
            },
            "description": "Infrastructure in Poor or Very Poor condition requiring priority attention",
        }
        
        return result

    def _fallback_cost_search(
        self,
        infrastructure_type: str,
        location: str,
        limit: int,
    ) -> dict[str, Any]:
        """
        Fallback to dataset search when direct StatCan data is not available.
        """
        datasets = []
        
        # Search for cost/investment datasets
        search_queries = [
            f"{infrastructure_type} cost investment infrastructure {location}",
            f"infrastructure economic accounts {location}",
            f"{infrastructure_type} replacement value {location}",
        ]
        
        seen_ids = set()
        for query in search_queries:
            search_results = self._search_datasets(query, limit=20)
            
            for ds in search_results.get("results", []):
                if ds.get("id") in seen_ids:
                    continue
                seen_ids.add(ds.get("id"))
                
                # Find CSV resources that might contain cost data
                csv_resources = [
                    {
                        "name": r.get("name"),
                        "format": r.get("format"),
                        "url": r.get("url"),
                    }
                    for r in ds.get("resources", [])
                    if r.get("format", "").upper() in ["CSV", "XLS", "XLSX"]
                ]
                
                dataset_info = {
                    "id": ds.get("id"),
                    "title": ds.get("title"),
                    "organization": ds.get("organization", {}).get("title"),
                    "description": ds.get("notes", "")[:300] if ds.get("notes") else "",
                    "data_resources": csv_resources[:5],
                }
                datasets.append(dataset_info)
                
                if len(datasets) >= limit:
                    break
            
            if len(datasets) >= limit:
                break
        
        return {
            "infrastructure_type": infrastructure_type,
            "location": location,
            "total_datasets": len(datasets),
            "datasets": datasets,
            "note": "Direct cost data not available for this infrastructure type. Dataset search results provided instead.",
        }

    def compare_across_regions(
        self,
        infrastructure_type: str,
        regions: list[str],
        metrics: list[str],
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Compare infrastructure across multiple regions.
        Returns comparative analysis with actual infrastructure counts and metrics.
        """
        comparison = {}
        
        for region in regions:
            region_data = {
                "region": region,
                "metrics": {},
                "sources": [],
            }
            
            # Query infrastructure based on type
            if infrastructure_type.lower() == "bridge":
                data = self.query_bridges(province=region, limit=limit)
                bridges = data.get("bridges", [])
                region_data["infrastructure_count"] = len(bridges)
                region_data["sources"] = data.get("sources", [])
                
                if "count" in metrics:
                    region_data["metrics"]["count"] = len(bridges)
                if "condition" in metrics:
                    conditions = [b.get("condition_rating") for b in bridges if b.get("condition_rating")]
                    region_data["metrics"]["condition_distribution"] = {
                        c: conditions.count(c) for c in set(conditions)
                    }
                if "age" in metrics:
                    years = [b.get("year_built") for b in bridges if b.get("year_built")]
                    if years:
                        try:
                            numeric_years = [int(y) for y in years if y]
                            if numeric_years:
                                region_data["metrics"]["age_stats"] = {
                                    "oldest": min(numeric_years),
                                    "newest": max(numeric_years),
                                    "average_year": round(sum(numeric_years) / len(numeric_years)),
                                }
                        except (ValueError, TypeError):
                            pass
                    
            elif infrastructure_type.lower() == "railway":
                data = self.query_railways(region=region, limit=limit)
                railways = data.get("railways", [])
                region_data["infrastructure_count"] = len(railways)
                region_data["sources"] = data.get("sources", [])
                
                if "count" in metrics:
                    region_data["metrics"]["count"] = len(railways)
                if "operator" in metrics:
                    operators = [r.get("operator") for r in railways if r.get("operator")]
                    region_data["metrics"]["operators"] = list(set(operators))
            
            comparison[region] = region_data
        
        return {
            "infrastructure_type": infrastructure_type,
            "regions": regions,
            "metrics_requested": metrics,
            "comparison": comparison,
        }
