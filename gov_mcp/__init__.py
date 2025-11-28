"""
Package initialization for gov_mcp.
"""

__version__ = "0.1.0"
__author__ = "Government MCP Team"
__description__ = "Model Context Protocol server for Canada's Open Government infrastructure data"

from gov_mcp.api_client import OpenGovCanadaClient
from gov_mcp.server import GovernmentMCPServer, main

__all__ = [
    "OpenGovCanadaClient",
    "GovernmentMCPServer",
    "main",
]
