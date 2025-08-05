#!/usr/bin/env python3
"""
Simple test MCP server for LiveKit agent integration

This creates a basic MCP server with calendar and time tools for testing.
"""

from mcp.server.fastmcp import FastMCP
from datetime import datetime

# Create MCP server
mcp = FastMCP("Test Calendar Server 📅")

@mcp.tool()
def get_current_time() -> str:
    """Get the current date and time."""
    now = datetime.now()
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"

@mcp.tool()
def add_calendar_event(title: str, date: str, time: str = "10:00") -> str:
    """Add an event to the calendar.
    
    Args:
        title: Event title
        date: Date in YYYY-MM-DD format  
        time: Time in HH:MM format (optional, defaults to 10:00)
    """
    return f"✅ Added calendar event: '{title}' on {date} at {time}"

@mcp.tool()
def list_calendar_events() -> str:
    """List upcoming calendar events."""
    # Mock calendar events
    events = [
        {"title": "Team Meeting", "date": "2024-12-30", "time": "14:00"},
        {"title": "Doctor Appointment", "date": "2024-12-31", "time": "09:30"},
        {"title": "New Year Party", "date": "2025-01-01", "time": "20:00"}
    ]
    
    result = "📅 Upcoming Events:\n"
    for event in events:
        result += f"• {event['title']} - {event['date']} at {event['time']}\n"
    
    return result

@mcp.tool()
def search_calendar(query: str) -> str:
    """Search calendar events by keyword.
    
    Args:
        query: Search term to look for in event titles
    """
    # Mock search results
    if "meeting" in query.lower():
        return "Found: Team Meeting on 2024-12-30 at 14:00"
    elif "doctor" in query.lower():
        return "Found: Doctor Appointment on 2024-12-31 at 09:30"
    elif "party" in query.lower():
        return "Found: New Year Party on 2025-01-01 at 20:00"
    else:
        return f"No events found matching '{query}'"

if __name__ == "__main__":
    # Run server with SSE transport (default port 8000)
    print("🚀 Starting Test MCP Server with SSE transport")
    print("📅 Available at: http://localhost:8000/sse")
    print("📅 Available tools: get_current_time, add_calendar_event, list_calendar_events, search_calendar")
    mcp.run(transport="sse") 