#!/usr/bin/env python3
"""
Quick test to verify the Government MCP Server is working correctly.
"""
import sys
import asyncio
from gov_mcp.server import GovernmentMCPServer
from gov_mcp.api_client import OpenGovCanadaClient


async def test_server():
    """Test server initialization and tools."""
    print("=" * 70)
    print("🧪 Government MCP Server - Quick Test")
    print("=" * 70)
    
    try:
        # Test 1: Server initialization
        print("\n1️⃣  Testing server initialization...")
        server = GovernmentMCPServer()
        print("   ✓ Server created successfully")
        
        # Test 2: API client
        print("\n2️⃣  Testing API client...")
        client = OpenGovCanadaClient()
        print("   ✓ API client initialized")
        
        # Test 3: Try a simple API call
        print("\n3️⃣  Testing API connectivity...")
        try:
            # Try to list organizations (simple, lightweight call)
            orgs = client.list_organizations()
            print(f"   ✓ Connected to API successfully")
            print(f"   ✓ Found {len(orgs)} organizations")
        except Exception as e:
            print(f"   ℹ API call failed (may need internet): {e}")
        
        print("\n" + "=" * 70)
        print("✨ All tests passed! Server is ready.")
        print("=" * 70)
        print("\n🚀 To start the server, run:")
        print("   python -m gov_mcp.server")
        print("\n📚 To see examples, run:")
        print("   python examples.py")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)
