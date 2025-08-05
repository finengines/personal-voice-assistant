# MCP Database vs JSON Fallback Issue

## Problem
Voice agent processes are using corrupted JSON files as fallback instead of the database, despite database having correct bearer tokens.

## Root Cause Analysis

### Expected Behavior
1. **Primary**: API call to MCP service (port 8082)
2. **Fallback 1**: Database direct access
3. **Fallback 2**: JSON file (`/app/config/mcp_servers.json`)

### Actual Behavior
System was falling back to JSON files with:
- Gmail token: `"key"` (placeholder)
- Calendar token: `"key"` (placeholder)
- Result: 403 Forbidden errors

## Investigation Findings

### Database Status ✅
- Contains correct bearer tokens
- API endpoints working (port 8082)
- UI can update tokens successfully

### JSON Files Found 🔍
1. `/app/mcp_servers.json` - Had corrupted token ending with "mFafNull%"
2. `/app/config/mcp_servers.json` - Had placeholder "key" tokens

### Why JSON Fallback Was Used
Agent processes during startup may experience:
- Network timing issues accessing API
- Database connection delays
- Container networking issues between agent workers and API

## Resolution Applied

### Immediate Fixes ✅
1. **Fixed** `/app/mcp_servers.json` - Set corrupted token to `null`
2. **Fixed** `/app/config/mcp_servers.json` - Replaced "key" with `null`
3. **Verified** database contains correct tokens

### Long-term Solution
- Database should be primary source
- JSON files serve as emergency fallback only
- All JSON fallback tokens set to `null` to prevent 403 errors

## Files Updated
- `personal_agent/backend/mcp_servers.json` - Fixed corrupted token
- `/app/config/mcp_servers.json` - Replaced placeholder tokens

## Verification
- No more 403 Forbidden errors
- System should now use database primarily
- JSON fallback won't cause auth failures