#!/usr/bin/env python3
"""
Test LiveKit connection with generated token
"""

import asyncio
import websockets
import json
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from generate_token import generate_livekit_token

async def test_livekit_connection():
    """Test LiveKit WebSocket connection"""
    
    # Generate a token
    token, room_name, participant_name = generate_livekit_token()
    print(f"Generated token for room: {room_name}")
    print(f"Participant: {participant_name}")
    
    # LiveKit WebSocket URL
    ws_url = f"ws://localhost:7883/rtc?access_token={token}&auto_subscribe=1"
    
    try:
        print(f"Connecting to: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ Successfully connected to LiveKit!")
            
            # Send a simple message
            message = {
                "type": "ping"
            }
            await websocket.send(json.dumps(message))
            print("✅ Sent ping message")
            
            # Wait for response
            response = await websocket.recv()
            print(f"✅ Received response: {response}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Testing LiveKit Connection")
    print("=" * 40)
    
    success = asyncio.run(test_livekit_connection())
    
    if success:
        print("\n✅ LiveKit connection test PASSED!")
        print("🎤 Your voice assistant should work now!")
    else:
        print("\n❌ LiveKit connection test FAILED!")
        print("🔧 Check LiveKit server logs for issues.") 