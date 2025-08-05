#!/usr/bin/env python3
"""
Test script for MCP edit functionality

This script tests that the edit functionality works correctly by:
1. Fetching server details
2. Modifying the configuration 
3. Updating the server
4. Verifying the changes
"""

import asyncio
import aiohttp
import json
import sys

API_BASE = "http://localhost:8082"
TEST_SERVER_ID = "example-sse"

async def test_edit_functionality():
    """Test the complete edit workflow"""
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing MCP Server Edit Functionality...")
        print("=" * 50)
        
        # Step 1: Fetch original server details
        print(f"📥 1. Fetching server details for '{TEST_SERVER_ID}'...")
        try:
            async with session.get(f"{API_BASE}/servers/{TEST_SERVER_ID}") as response:
                if response.status == 200:
                    data = await response.json()
                    original_config = data['data']['config']
                    print(f"   ✅ Original name: '{original_config['name']}'")
                    print(f"   ✅ Original description: '{original_config['description']}'")
                    print(f"   ✅ Original enabled: {original_config['enabled']}")
                else:
                    print(f"   ❌ Failed to fetch server: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Error fetching server: {e}")
            return False
        
        # Step 2: Prepare updated configuration
        print(f"\n📝 2. Preparing updated configuration...")
        updated_config = original_config.copy()
        updated_config['name'] = "Updated Test Server"
        updated_config['description'] = "This server was updated via API test"
        updated_config['enabled'] = not original_config['enabled']  # Toggle enabled state
        
        print(f"   ✅ New name: '{updated_config['name']}'")
        print(f"   ✅ New description: '{updated_config['description']}'")
        print(f"   ✅ New enabled: {updated_config['enabled']}")
        
        # Step 3: Update the server via PUT request
        print(f"\n📤 3. Updating server configuration...")
        try:
            headers = {'Content-Type': 'application/json'}
            async with session.put(
                f"{API_BASE}/servers/{TEST_SERVER_ID}", 
                data=json.dumps(updated_config),
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ Update successful: {result['message']}")
                else:
                    print(f"   ❌ Update failed: {response.status}")
                    error_text = await response.text()
                    print(f"   ❌ Error: {error_text}")
                    return False
        except Exception as e:
            print(f"   ❌ Error updating server: {e}")
            return False
        
        # Step 4: Verify the changes were applied
        print(f"\n🔍 4. Verifying changes were applied...")
        try:
            async with session.get(f"{API_BASE}/servers/{TEST_SERVER_ID}") as response:
                if response.status == 200:
                    data = await response.json()
                    verified_config = data['data']['config']
                    
                    # Check if changes were applied
                    name_correct = verified_config['name'] == updated_config['name']
                    desc_correct = verified_config['description'] == updated_config['description']
                    enabled_correct = verified_config['enabled'] == updated_config['enabled']
                    
                    print(f"   ✅ Name updated: {name_correct} ('{verified_config['name']}')")
                    print(f"   ✅ Description updated: {desc_correct}")
                    print(f"   ✅ Enabled state updated: {enabled_correct} ({verified_config['enabled']})")
                    
                    if name_correct and desc_correct and enabled_correct:
                        print(f"\n🎉 All changes verified successfully!")
                    else:
                        print(f"\n❌ Some changes were not applied correctly!")
                        return False
                else:
                    print(f"   ❌ Failed to verify changes: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Error verifying changes: {e}")
            return False
        
        # Step 5: Restore original configuration 
        print(f"\n🔄 5. Restoring original configuration...")
        try:
            headers = {'Content-Type': 'application/json'}
            async with session.put(
                f"{API_BASE}/servers/{TEST_SERVER_ID}", 
                data=json.dumps(original_config),
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"   ✅ Original configuration restored")
                else:
                    print(f"   ⚠️  Warning: Failed to restore original config: {response.status}")
        except Exception as e:
            print(f"   ⚠️  Warning: Error restoring original config: {e}")
        
        return True

async def main():
    """Main test function"""
    print("🔧 MCP Edit Functionality Test")
    print("=" * 50)
    
    # Test if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    print("❌ MCP API server is not responding.")
                    return 1
    except Exception as e:
        print("❌ MCP API server is not running.")
        print(f"   Error: {e}")
        return 1
    
    # Run edit functionality test
    success = await test_edit_functionality()
    
    if success:
        print("\n🎉 Edit functionality test passed!")
        print("✅ The edit feature is working correctly")
        return 0
    else:
        print("\n❌ Edit functionality test failed!")
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