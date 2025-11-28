"""
HTTP client with retry logic for transportation infrastructure API.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for HTTP retry behavior."""
    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_status_codes: list[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    timeout: int = 30


class HTTPClient:
    """HTTP client with retry logic."""
    
    def __init__(self, base_url: str, retry_config: Optional[RetryConfig] = None):
        self.base_url = base_url.rstrip("/")
        self.config = retry_config or RetryConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "GOV-CA-Transportation-MCP/0.1.0",
            "Accept": "application/json",
        })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=self.config.timeout,
                )
                
                if response.status_code in self.config.retry_status_codes:
                    if attempt < self.config.max_retries:
                        wait_time = self.config.backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Request to {url} returned {response.status_code}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries:
                    wait_time = self.config.backoff_factor * (2 ** attempt)
                    logger.warning(f"Request timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"{method} request failed for {url}: {e}")
                raise
        
        raise requests.exceptions.RetryError(f"Max retries exceeded for {url}")
    
    def get(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make GET request."""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, json_data: Optional[dict] = None) -> dict[str, Any]:
        """Make POST request."""
        return self._make_request("POST", endpoint, json_data=json_data)
