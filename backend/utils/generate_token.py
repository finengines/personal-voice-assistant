#!/usr/bin/env python3
"""
LiveKit Token Generator for Development

This script generates proper JWT tokens for connecting to the LiveKit dev server.
"""

import jwt
import time
import uuid
from datetime import datetime, timedelta

# LiveKit dev server configuration
LIVEKIT_API_KEY = "devkey"
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "your_secret_key_at_least_32_characters_long")

def generate_livekit_token(room_name: str = None, participant_name: str = None, duration_hours: int = 24):
    """
    Generate a LiveKit JWT token for development.
    
    Args:
        room_name: Name of the room to join (optional)
        participant_name: Name of the participant (optional)
        duration_hours: Token validity duration in hours
    
    Returns:
        JWT token string
    """
    
    # Generate defaults if not provided
    if not room_name:
        room_name = f"voice-assistant-{int(time.time())}"
    
    if not participant_name:
        participant_name = f"user-{uuid.uuid4().hex[:8]}"
    
    # Token payload
    now = datetime.utcnow()
    exp = now + timedelta(hours=duration_hours)
    
    payload = {
        "iss": LIVEKIT_API_KEY,
        "sub": LIVEKIT_API_KEY,
        "jti": str(uuid.uuid4()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True
        },
        "metadata": f"participant_name:{participant_name}"
    }
    
    # Generate JWT token
    token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
    
    return token, room_name, participant_name

def main():
    """Generate and display a LiveKit token."""
    print("🎤 LiveKit Token Generator for Voice Assistant")
    print("=" * 50)
    
    # Generate token
    token, room_name, participant_name = generate_livekit_token()
    
    print(f"📋 Token Details:")
    print(f"   Room: {room_name}")
    print(f"   Participant: {participant_name}")
    print(f"   Valid for: 24 hours")
    print()
    print(f"🔑 Generated Token:")
    print(f"   {token}")
    print()
    print("💡 Instructions:")
    print("   1. Copy the token above")
    print("   2. Paste it in the frontend token field")
    print("   3. Click 'Connect' to join the voice assistant")
    print()
    print("⚠️  Note: This token is for development only!")
    print("   In production, use proper token generation with your API keys.")

if __name__ == "__main__":
    main() 