"""
HTTP client with retry logic for Open Government Canada API.
"""
import time
import logging
from typing import Any, Optional, Dict
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for HTTP retry logic."""
    max_retries: int = 3
    backoff_factor: float = 1.0
    timeout: int = 30
    status_forcelist: tuple = (500, 502, 504)


class HTTPClient:
    """HTTP client with automatic retry logic."""

    def __init__(self, base_url: str, config: Optional[RetryConfig] = None):
        """
        Initialize HTTP client with retry logic.
        
        Args:
            base_url: Base URL for all requests
            config: Retry configuration
        """
        self.base_url = base_url
        self.config = config or RetryConfig()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=self.config.status_forcelist,
            allowed_methods=["GET", "POST", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            "User-Agent": "gov-mcp-server/0.1.0",
            "Accept": "application/json",
        })
        
        return session

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            **kwargs: Additional requests arguments
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        kwargs.setdefault("timeout", self.config.timeout)
        
        try:
            logger.debug(f"GET {url} with params {params}")
            response = self.session.get(url, params=params, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"GET request failed for {url}: {e}")
            raise

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            json_data: JSON body data
            params: Query parameters
            **kwargs: Additional requests arguments
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        kwargs.setdefault("timeout", self.config.timeout)
        
        try:
            logger.debug(f"POST {url} with json {json_data}")
            response = self.session.post(url, json=json_data, params=params, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"POST request failed for {url}: {e}")
            raise
