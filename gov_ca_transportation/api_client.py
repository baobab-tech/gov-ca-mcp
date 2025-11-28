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
        "cycling": {
            "montreal": {
                "province": "Quebec",
                "city": "Montreal",
                "geojson_url": "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson",
                "name": "Montreal Bicycle Network",
                "format": "geojson",
            },
            "toronto": {
                "province": "Ontario",
                "city": "Toronto",
                "geojson_url": "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/abbe5ee3-e249-4f86-a219-f0022eaddcc9/resource/023da9a2-8848-4e10-9cad-e7f9119cd874/download/cycling-network-4326.geojson",
                "name": "Toronto Cycling Network",
                "format": "geojson",
            },
            "quebec_city": {
                "province": "Quebec",
                "city": "Quebec City",
                "geojson_url": "https://www.donneesquebec.ca/recherche/dataset/7e359f54-b8d7-45aa-abaa-2f2135ad05f1/resource/1c7ba52f-92d4-47f2-a255-850f822d9ed8/download/reseau_cyclable.geojson",
                "name": "Quebec City Bicycle Network",
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
        Returns actual bridge records with location, condition, and metadata.
        Dynamically selects data sources based on province/city filters.
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
        
        # Calculate per-source limit to distribute records evenly when no filter
        num_sources = len(sources_to_query)
        if num_sources > 0 and not province and not city:
            # Distribute limit across sources, with remainder going to first sources
            per_source_limit = max(limit // num_sources, 10)
        else:
            per_source_limit = limit
        
        # Query each applicable source
        for key, resource in sources_to_query:
            if len(bridges) >= limit:
                break
            
            # Calculate how many more records we can fetch from this source
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
        
        # If no specific source matched, search Open Data API
        if not sources_to_query or len(bridges) < limit:
            search_query = "bridge infrastructure structure"
            if province:
                search_query += f" {province}"
            if city:
                search_query += f" {city}"
            
            search_results = self._search_datasets(search_query, limit=10)
            
            for ds in search_results.get("results", []):
                if len(bridges) >= limit:
                    break
                    
                for res in ds.get("resources", []):
                    fmt = res.get("format", "").upper()
                    url = res.get("url", "")
                    
                    if fmt == "GEOJSON" and url:
                        try:
                            geojson = self._fetch_geojson(url)
                            sources_queried.append(ds.get("title", "Unknown"))
                            
                            for feature in geojson.get("features", []):
                                if len(bridges) >= limit:
                                    break
                                props = feature.get("properties", {})
                                geom = feature.get("geometry", {})
                                coords = self._extract_coordinates(geom)
                                
                                bridge_record = {
                                    "id": props.get("id") or props.get("ID"),
                                    "name": props.get("name") or props.get("NAME") or props.get("nom"),
                                    "structure_type": props.get("type") or props.get("TYPE") or "bridge",
                                    "condition_rating": props.get("condition"),
                                    "location": {"coordinates": coords},
                                    "properties": props,
                                    "geometry": geom,
                                    "source": ds.get("title"),
                                }
                                bridges.append(bridge_record)
                        except Exception:
                            continue
        
        return {
            "count": len(bridges),
            "bridges": bridges[:limit],
            "sources": list(set(sources_queried)),
            "filters_applied": {
                "province": province,
                "city": city,
                "condition": condition,
                "capacity_min": capacity_min,
                "built_after": built_after,
            },
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

    def query_transit_stops(
        self,
        city: str,
        route_types: Optional[list[str]] = None,
        accessibility: Optional[bool] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get public transit stop infrastructure.
        Returns actual transit stop locations with service info.
        Note: Most Canadian transit data is in GTFS format (ZIP archives).
        For detailed stop/route data, use get_gtfs_feed() to access GTFS data.
        """
        stops = []
        sources_queried = []
        gtfs_sources = []
        
        # Search for transit/GTFS datasets - be more specific to get actual transit data
        search_queries = [
            f"bus metro transit stops {city}",
            f"GTFS transit schedule {city}",
            f"public transit {city}",
        ]
        
        seen_datasets = set()
        for search_query in search_queries:
            search_results = self._search_datasets(search_query, limit=10)
            
            for ds in search_results.get("results", []):
                ds_id = ds.get("id")
                if ds_id in seen_datasets:
                    continue
                seen_datasets.add(ds_id)
                
                # Skip datasets that don't look like transit data
                title_lower = ds.get("title", "").lower()
                if not any(kw in title_lower for kw in ["transit", "bus", "metro", "stm", "gtfs", "ttc", "translink", "oc transpo"]):
                    continue
                
                if len(stops) >= limit:
                    break
                for res in ds.get("resources", []):
                    fmt = res.get("format", "").upper()
                    url = res.get("url", "")
                    
                    # Track GTFS sources for reference
                    if fmt in ["GTFS", "ZIP"] and ("gtfs" in url.lower() or "gtfs" in res.get("name", "").lower()):
                        gtfs_sources.append({
                            "name": ds.get("title"),
                            "url": url,
                            "format": fmt,
                        })
                        continue
                
                if fmt == "GEOJSON" and url:
                    try:
                        geojson = self._fetch_geojson(url)
                        sources_queried.append(ds.get("title", "Unknown"))
                        
                        for feature in geojson.get("features", []):
                            if len(stops) >= limit:
                                break
                            props = feature.get("properties", {})
                            geom = feature.get("geometry", {})
                            coords = self._extract_coordinates(geom)
                            
                            stop = {
                                "id": props.get("stop_id") or props.get("id"),
                                "name": props.get("stop_name") or props.get("name"),
                                "location": {"city": city, "coordinates": coords},
                                "properties": props,
                                "geometry": geom,
                                "source": ds.get("title"),
                            }
                            stops.append(stop)
                    except Exception:
                        continue
        
        # Add GTFS recommendation if no GeoJSON stops found
        gtfs_note = None
        if not stops and gtfs_sources:
            gtfs_note = "No GeoJSON transit stop data found. Consider using get_gtfs_feed() to access GTFS data for detailed stop information."
        
        return {
            "count": len(stops),
            "transit_stops": stops[:limit],
            "city": city,
            "sources": list(set(sources_queried)),
            "gtfs_available": gtfs_sources[:5] if gtfs_sources else [],
            "note": gtfs_note,
            "filters_applied": {
                "route_types": route_types,
                "accessibility": accessibility,
            },
        }

    def get_gtfs_feed(
        self,
        transit_agency: str,
        include_realtime: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Access transit data in GTFS format.
        Returns GTFS feed information and download links.
        """
        feeds = []
        sources_queried = []
        
        # Search for GTFS datasets
        search_query = f"GTFS transit {transit_agency}"
        search_results = self._search_datasets(search_query, limit=limit)
        
        for ds in search_results.get("results", []):
            gtfs_resources = []
            
            for resource in ds.get("resources", []):
                fmt = resource.get("format", "").upper()
                name = (resource.get("name") or "").lower()
                url = resource.get("url", "")
                
                # GTFS feeds are usually ZIP files or OTHER format
                is_gtfs = fmt in ["ZIP", "OTHER", "GTFS"] or "gtfs" in name
                is_realtime = "realtime" in name or "rt" in name or "real-time" in name
                
                if is_gtfs:
                    gtfs_resources.append({
                        "id": resource.get("id"),
                        "name": resource.get("name"),
                        "format": fmt,
                        "url": url,
                        "is_realtime": is_realtime,
                    })
            
            if gtfs_resources:
                sources_queried.append(ds.get("title"))
                
                # Filter by realtime if requested
                if include_realtime:
                    filtered_resources = gtfs_resources
                else:
                    filtered_resources = [r for r in gtfs_resources if not r.get("is_realtime")]
                    if not filtered_resources:
                        filtered_resources = gtfs_resources
                
                feed = {
                    "dataset_id": ds.get("id"),
                    "agency_name": ds.get("title"),
                    "organization": ds.get("organization", {}).get("title"),
                    "description": ds.get("notes", "")[:300] if ds.get("notes") else "",
                    "gtfs_resources": filtered_resources,
                    "has_realtime": any(r.get("is_realtime") for r in gtfs_resources),
                    "download_urls": [r["url"] for r in filtered_resources if r.get("url")],
                }
                feeds.append(feed)
        
        return {
            "count": len(feeds),
            "gtfs_feeds": feeds[:limit],
            "transit_agency": transit_agency,
            "include_realtime": include_realtime,
            "sources": list(set(sources_queried)),
        }

    def query_cycling_networks(
        self,
        municipality: Optional[str] = None,
        province: Optional[str] = None,
        surface_type: Optional[str] = None,
        protected: Optional[bool] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get cycling path and lane data across Canada.
        Returns actual cycling infrastructure records with GeoJSON.
        Dynamically selects data sources based on municipality/province filters.
        """
        paths = []
        sources_queried = []
        
        # Normalize filters for matching
        muni_lower = municipality.lower() if municipality else None
        prov_lower = province.lower() if province else None
        
        # Determine which sources to query based on filters
        sources_to_query = []
        for key, resource in self.KNOWN_RESOURCES.get("cycling", {}).items():
            res_province = (resource.get("province") or "").lower()
            res_city = (resource.get("city") or "").lower()
            
            # If no filters, query all sources
            if not municipality and not province:
                sources_to_query.append((key, resource))
            # If municipality matches city
            elif muni_lower and muni_lower in res_city:
                sources_to_query.append((key, resource))
            # If province matches
            elif prov_lower and prov_lower in res_province:
                sources_to_query.append((key, resource))
            # Province abbreviation matching
            elif prov_lower in ["qc", "québec"] and "quebec" in res_province:
                sources_to_query.append((key, resource))
            elif prov_lower in ["on"] and "ontario" in res_province:
                sources_to_query.append((key, resource))
        
        # Calculate per-source limit to distribute records evenly when no filter
        num_sources = len(sources_to_query)
        if num_sources > 0 and not municipality and not province:
            per_source_limit = max(limit // num_sources, 10)
        else:
            per_source_limit = limit
        
        # Query each applicable source
        source_record_count = 0
        for key, resource in sources_to_query:
            if len(paths) >= limit:
                break
            
            source_record_count = 0
            remaining = limit - len(paths)
            source_limit = min(per_source_limit, remaining)
                
            try:
                geojson = self._fetch_geojson(resource["geojson_url"])
                sources_queried.append(resource["name"])
                res_city = resource.get("city", "")
                res_province = resource.get("province", "")
                
                for feature in geojson.get("features", []):
                    if source_record_count >= source_limit or len(paths) >= limit:
                        break
                        
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    coords = self._extract_coordinates(geom)
                    
                    # Parse based on source
                    if "montreal" in key.lower():
                        path = self._parse_montreal_cycling(props, geom, coords, resource, protected)
                    elif "toronto" in key.lower():
                        path = self._parse_toronto_cycling(props, geom, coords, resource, protected)
                    else:
                        path = self._parse_generic_cycling(props, geom, coords, resource, res_city, res_province)
                    
                    if path:
                        paths.append(path)
                        source_record_count += 1
                        
            except Exception as e:
                logger.warning(f"Could not fetch cycling data from {resource.get('name')}: {e}")
        
        # Search for additional cycling datasets if needed
        if len(paths) < limit:
            search_query = "cycling bike lane path"
            if municipality:
                search_query += f" {municipality}"
            if province:
                search_query += f" {province}"
            
            search_results = self._search_datasets(search_query, limit=10)
            
            for ds in search_results.get("results", []):
                if len(paths) >= limit:
                    break
                for res in ds.get("resources", []):
                    fmt = res.get("format", "").upper()
                    url = res.get("url", "")
                    
                    if fmt == "GEOJSON" and url:
                        try:
                            geojson = self._fetch_geojson(url)
                            sources_queried.append(ds.get("title", "Unknown"))
                            
                            for feature in geojson.get("features", []):
                                if len(paths) >= limit:
                                    break
                                props = feature.get("properties", {})
                                geom = feature.get("geometry", {})
                                coords = self._extract_coordinates(geom)
                                
                                path = {
                                    "id": props.get("id") or props.get("ID"),
                                    "name": props.get("name") or props.get("nom"),
                                    "path_type": props.get("type") or props.get("TYPE"),
                                    "location": {
                                        "municipality": municipality,
                                        "coordinates": coords,
                                    },
                                    "properties": props,
                                    "geometry": geom,
                                    "source": ds.get("title"),
                                }
                                paths.append(path)
                        except Exception:
                            continue
        
        return {
            "count": len(paths),
            "cycling_paths": paths[:limit],
            "municipality": municipality,
            "province": province,
            "sources": list(set(sources_queried)),
            "filters_applied": {
                "surface_type": surface_type,
                "protected": protected,
            },
        }

    def _parse_montreal_cycling(self, props: dict, geom: dict, coords: dict, resource: dict, protected: Optional[bool]) -> Optional[dict]:
        """Parse Montreal cycling data with correct field names."""
        path_type_code = props.get("TYPE_VOIE_CODE")
        path_type_desc = props.get("TYPE_VOIE_DESC") or props.get("TYPE_VOIE2_DESC")
        separator_desc = props.get("SEPARATEUR_DESC")
        is_protected = props.get("PROTEGE_4S") == 1 or (separator_desc and "protégé" in separator_desc.lower())
        is_four_seasons = props.get("SAISONS4") == 1
        
        if protected is not None and is_protected != protected:
            return None
        
        return {
            "id": props.get("ID_CYCL") or props.get("ID_TRC"),
            "neighborhood": props.get("NOM_ARR_VILLE_DESC"),
            "path_type_code": path_type_code,
            "path_type": path_type_desc,
            "separator": separator_desc,
            "protected": is_protected,
            "four_seasons": is_four_seasons,
            "length_m": props.get("LONGUEUR"),
            "num_lanes": props.get("NBR_VOIE"),
            "is_route_verte": props.get("ROUTE_VERTE") == 1,
            "location": {
                "city": "Montreal",
                "province": "Quebec",
                "neighborhood": props.get("NOM_ARR_VILLE_DESC"),
                "coordinates": coords,
            },
            "geometry": geom,
            "source": resource["name"],
        }

    def _parse_toronto_cycling(self, props: dict, geom: dict, coords: dict, resource: dict, protected: Optional[bool]) -> Optional[dict]:
        """Parse Toronto cycling data."""
        # Toronto uses different field names
        route_type = props.get("INFRA_HIGHORDER") or props.get("CLASSIFICATION")
        is_protected = route_type and ("cycle track" in route_type.lower() or "protected" in route_type.lower())
        
        if protected is not None and is_protected != protected:
            return None
        
        return {
            "id": props.get("_id") or props.get("OBJECTID"),
            "name": props.get("STREET_NAME") or props.get("LINEAR_NAME_FULL"),
            "path_type": route_type,
            "classification": props.get("CLASSIFICATION"),
            "status": props.get("STATUS") or props.get("INSTALLED"),
            "protected": is_protected,
            "bike_lane_type": props.get("BIKE_LANE_TYPE"),
            "length_m": props.get("Shape__Length"),
            "location": {
                "city": "Toronto",
                "province": "Ontario",
                "coordinates": coords,
            },
            "geometry": geom,
            "source": resource["name"],
        }

    def _parse_generic_cycling(self, props: dict, geom: dict, coords: dict, resource: dict, city: str, province: str) -> dict:
        """Parse generic cycling data."""
        return {
            "id": props.get("id") or props.get("ID") or props.get("_id"),
            "name": props.get("name") or props.get("nom") or props.get("NAME"),
            "path_type": props.get("type") or props.get("TYPE") or props.get("type_voie"),
            "surface": props.get("surface") or props.get("SURFACE"),
            "length_m": props.get("length") or props.get("LONGUEUR"),
            "location": {
                "city": city,
                "province": province,
                "coordinates": coords,
            },
            "properties": props,
            "geometry": geom,
            "source": resource["name"],
        }
        type_map = {
            "1": "Separated bike path",
            "2": "On-street bike lane",
            "3": "Shared lane (sharrow)",
            "4": "Multi-use path",
            "5": "Protected bike lane",
        }
        return type_map.get(str(type_code), str(type_code) if type_code else "Unknown")

    def analyze_bridge_conditions(
        self,
        region: str,
        group_by: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Aggregate bridge condition data for analysis.
        Returns statistical analysis of bridge conditions.
        """
        # Get bridge data for the region
        bridges_data = self.query_bridges(province=region, limit=limit)
        bridges = bridges_data.get("bridges", [])
        
        if not bridges:
            return {
                "region": region,
                "error": "No bridge data available for this region",
                "sources": bridges_data.get("sources", []),
                "suggestion": "Try 'Quebec' or 'Montreal' for available bridge data",
            }
        
        # Aggregate condition statistics
        condition_counts = {"good": 0, "fair": 0, "poor": 0, "critical": 0, "unknown": 0}
        total_bridges = len(bridges)
        
        for bridge in bridges:
            condition = bridge.get("condition_rating", "unknown")
            if condition in condition_counts:
                condition_counts[condition] += 1
            else:
                condition_counts["unknown"] += 1
        
        # Group by if specified
        grouped_data = {}
        if group_by and group_by in ["city", "structure_type", "condition"]:
            for bridge in bridges:
                if group_by == "city":
                    key = bridge.get("location", {}).get("city", "Unknown")
                elif group_by == "structure_type":
                    key = bridge.get("structure_type", "Unknown")
                else:
                    key = bridge.get("condition_rating", "unknown")
                
                if key not in grouped_data:
                    grouped_data[key] = {"count": 0, "bridges": []}
                grouped_data[key]["count"] += 1
                if len(grouped_data[key]["bridges"]) < 5:  # Limit examples
                    grouped_data[key]["bridges"].append(bridge.get("name") or bridge.get("id"))
        
        return {
            "region": region,
            "total_bridges": total_bridges,
            "condition_summary": {
                "good": {"count": condition_counts["good"], "percentage": round(100 * condition_counts["good"] / total_bridges, 1) if total_bridges else 0},
                "fair": {"count": condition_counts["fair"], "percentage": round(100 * condition_counts["fair"] / total_bridges, 1) if total_bridges else 0},
                "poor": {"count": condition_counts["poor"], "percentage": round(100 * condition_counts["poor"] / total_bridges, 1) if total_bridges else 0},
                "critical": {"count": condition_counts["critical"], "percentage": round(100 * condition_counts["critical"] / total_bridges, 1) if total_bridges else 0},
                "unknown": {"count": condition_counts["unknown"], "percentage": round(100 * condition_counts["unknown"] / total_bridges, 1) if total_bridges else 0},
            },
            "grouped_by": group_by,
            "groups": grouped_data if grouped_data else None,
            "sources": bridges_data.get("sources", []),
        }

    def analyze_transit_coverage(
        self,
        city: str,
        radius_meters: int = 400,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Analyze transit accessibility coverage.
        Returns coverage analysis with statistics.
        """
        # Get transit stops for the city
        stops_data = self.query_transit_stops(city=city, limit=limit)
        stops = stops_data.get("transit_stops", [])
        
        if not stops:
            return {
                "city": city,
                "radius_meters": radius_meters,
                "error": "No transit stop data available for this city",
                "sources": stops_data.get("sources", []),
                "suggestion": "Try a major city like 'Toronto', 'Vancouver', or 'Montreal'",
            }
        
        # Aggregate statistics
        total_stops = len(stops)
        accessible_stops = sum(1 for s in stops if s.get("wheelchair_accessible"))
        bike_friendly_stops = sum(1 for s in stops if s.get("bikes_allowed"))
        
        # Group by agency
        agencies = {}
        for stop in stops:
            agency = stop.get("agency") or "Unknown"
            if agency not in agencies:
                agencies[agency] = {"stop_count": 0, "accessible": 0}
            agencies[agency]["stop_count"] += 1
            if stop.get("wheelchair_accessible"):
                agencies[agency]["accessible"] += 1
        
        # Group by route type
        route_types = {}
        for stop in stops:
            rt = stop.get("route_type") or "Unknown"
            rt_str = str(rt)
            if rt_str not in route_types:
                route_types[rt_str] = 0
            route_types[rt_str] += 1
        
        return {
            "city": city,
            "radius_meters": radius_meters,
            "coverage_analysis": {
                "total_stops": total_stops,
                "wheelchair_accessible": accessible_stops,
                "accessibility_percentage": round(100 * accessible_stops / total_stops, 1) if total_stops else 0,
                "bike_friendly": bike_friendly_stops,
                "bike_percentage": round(100 * bike_friendly_stops / total_stops, 1) if total_stops else 0,
            },
            "by_agency": agencies,
            "by_route_type": route_types,
            "note": f"Coverage radius of {radius_meters}m is typical walking distance to transit",
            "sources": stops_data.get("sources", []),
        }

    def get_infrastructure_costs(
        self,
        infrastructure_type: str,
        location: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Get cost data for transportation infrastructure.
        Returns replacement cost estimates and investment datasets.
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
            "note": "Cost data is typically in CSV format. Download resources for detailed cost/investment figures.",
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
                    
            elif infrastructure_type.lower() == "transit":
                # Use representative city for each region
                city_map = {
                    "ontario": "Toronto",
                    "quebec": "Montreal",
                    "british columbia": "Vancouver",
                    "alberta": "Calgary",
                    "manitoba": "Winnipeg",
                    "saskatchewan": "Saskatoon",
                }
                city = city_map.get(region.lower(), region)
                data = self.query_transit_stops(city=city, limit=limit)
                stops = data.get("transit_stops", [])
                region_data["infrastructure_count"] = len(stops)
                region_data["sources"] = data.get("sources", [])
                region_data["city_queried"] = city
                
                if "count" in metrics:
                    region_data["metrics"]["count"] = len(stops)
                if "accessibility" in metrics:
                    accessible = sum(1 for s in stops if s.get("wheelchair_accessible"))
                    region_data["metrics"]["accessibility"] = {
                        "accessible_stops": accessible,
                        "percentage": round(100 * accessible / len(stops), 1) if stops else 0,
                    }
                    
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
                    
            elif infrastructure_type.lower() == "cycling":
                city_map = {
                    "ontario": "Toronto",
                    "quebec": "Montreal",
                    "british columbia": "Vancouver",
                }
                city = city_map.get(region.lower(), region)
                data = self.query_cycling_networks(municipality=city, limit=limit)
                paths = data.get("cycling_paths", [])
                region_data["infrastructure_count"] = len(paths)
                region_data["sources"] = data.get("sources", [])
                region_data["city_queried"] = city
                
                if "count" in metrics:
                    region_data["metrics"]["count"] = len(paths)
                if "protected" in metrics:
                    protected = sum(1 for p in paths if p.get("protected"))
                    region_data["metrics"]["protected_lanes"] = {
                        "count": protected,
                        "percentage": round(100 * protected / len(paths), 1) if paths else 0,
                    }
            
            comparison[region] = region_data
        
        return {
            "infrastructure_type": infrastructure_type,
            "regions": regions,
            "metrics_requested": metrics,
            "comparison": comparison,
        }
