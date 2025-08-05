# MCP Bearer Token Corruption Bug Analysis

## Issue Summary
MCP servers (Gmail and Calendar) were returning 403 Forbidden errors due to corrupted bearer tokens ending with "Null%".

## Root Cause Analysis

### The Corrupted Token
```
Original: "XOMHbp/5h+8JvrBeBjNihfolo7k/2Y3ASdgFFdF6X3+62eG61Ehgnp14mFafNull%"
Problem: Ends with "mFafNull%" instead of proper base64
```

### Investigation Findings

1. **Location**: Found in `personal_agent/backend/mcp_servers.json` (line 14)
2. **Pattern**: Token ends with "Null%" indicating:
   - URL encoding applied (`%` character)
   - JavaScript `null` converted to string "Null"
   - Likely frontend-to-backend data corruption

3. **System Impact**: 
   - Database has correct tokens (verified via API)
   - JSON file serves as fallback when database unavailable
   - Agent initialization may have used corrupted JSON during database connection issues

### Technical Analysis

**URL Encoding Evidence:**
- The `%` character at the end is classic URL encoding
- "Null" suggests JavaScript `null` → `"Null"` → URL encoded

**Possible Corruption Path:**
```
Valid Token → Frontend Form → JavaScript null handling → URL encoding → "TokenNull%"
```

### Resolution

1. **Immediate Fix**: 
   - Set corrupted token to `null` in JSON file
   - Database already contains correct tokens from UI updates

2. **Prevention**: 
   - Database is primary source (JSON is backup only)
   - Frontend UI properly validates and saves tokens

### Files Affected
- `personal_agent/backend/mcp_servers.json` - Fixed corrupted token
- Database - Already contained correct tokens

### Verification
- ✅ 403 Forbidden errors resolved
- ✅ Database contains valid tokens
- ✅ JSON fallback cleaned up
- ✅ System functioning normally

## Lessons Learned
- JSON files should be considered legacy/backup only
- Database-first approach prevents such corruption
- URL encoding in auth tokens indicates data pipeline issues
- Fallback systems need the same validation as primary systems