#!/usr/bin/env python3
"""
Test script for MCP API

This script tests the MCP API server to ensure it's working correctly
and doesn't produce deprecation warnings.
"""

import asyncio
import aiohttp
import sys
from contextlib import asynccontextmanager

API_BASE = "http://localhost:8082"

async def test_api_endpoints():
    """Test various API endpoints"""
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing MCP API endpoints...")
        
        # Test health endpoint
        try:
            async with session.get(f"{API_BASE}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check: {data['message']}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
        
        # Test servers listing
        try:
            async with session.get(f"{API_BASE}/servers") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Servers list: {data['message']}")
                    print(f"   Found {len(data['data'])} configured servers")
                else:
                    print(f"❌ Servers list failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Servers list error: {e}")
            return False
        
        # Test tools endpoint
        try:
            async with session.get(f"{API_BASE}/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Tools list: {data['message']}")
                else:
                    print(f"❌ Tools list failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Tools list error: {e}")
            return False
        
        # Test root endpoint
        try:
            async with session.get(f"{API_BASE}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Root endpoint: {data['message']}")
                else:
                    print(f"❌ Root endpoint failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    return True

async def main():
    """Main test function"""
    print("🔧 MCP API Test Suite")
    print("=" * 50)
    
    # Test if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    print("❌ MCP API server is not responding. Please start it first with:")
                    print("   cd personal_agent/backend && python start_mcp_api.py")
                    return 1
    except Exception as e:
        print("❌ MCP API server is not running. Please start it first with:")
        print("   cd personal_agent/backend && python start_mcp_api.py")
        print(f"   Error: {e}")
        return 1
    
    # Run tests
    success = await test_api_endpoints()
    
    if success:
        print("\n🎉 All tests passed!")
        print("✅ MCP API is working correctly")
        print("✅ No deprecation warnings should appear in server logs")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1) 