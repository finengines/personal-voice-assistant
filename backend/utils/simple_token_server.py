#!/usr/bin/env python3
"""
Simple LiveKit Token Server for Development and Production

This server provides a simple HTTP endpoint for generating LiveKit tokens.
"""

import os
import json
import time
import uuid
import jwt
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# LiveKit configuration
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "your_secret_key_at_least_32_characters_long")

def generate_livekit_token(room_name: str = None, participant_name: str = None, preset_id: str = None, duration_hours: int = 24):
    """Generate a LiveKit JWT token."""
    
    if not room_name:
        base_room_name = f"voice-assistant-{int(time.time())}"
        # Include preset_id in room name if provided
        if preset_id:
            room_name = f"{base_room_name}--preset-{preset_id}"
        else:
            room_name = base_room_name
    
    if not participant_name:
        participant_name = f"user-{uuid.uuid4().hex[:8]}"
    
    now = datetime.utcnow()
    exp = now + timedelta(hours=duration_hours)
    
    metadata = {
        "participant_name": participant_name,
    }

    if preset_id:
        metadata["preset_id"] = preset_id

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
        "metadata": json.dumps(metadata)
    }
    
    token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
    
    return {
        "token": token,
        "room": room_name,
        "participant": participant_name,
        "expires": exp.isoformat(),
        "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    }

class SimpleTokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for token generation."""
        try:
            print(f"Received request: {self.path}")
            
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            room_name = query_params.get('room', [None])[0]
            participant_name = query_params.get('participant', [None])[0]
            preset_id = query_params.get('preset_id', [None])[0]
            
            # Generate token
            token_data = generate_livekit_token(room_name, participant_name, preset_id)
            
            # Set CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Return JSON response
            response = json.dumps(token_data, indent=2)
            self.wfile.write(response.encode())
            
            print(f"Generated token for room: {token_data['room']}")
            
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = json.dumps({"error": str(e)})
            self.wfile.write(error_response.encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to log messages to stdout"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    """Start the simple token server."""
    port = int(os.getenv("TOKEN_SERVER_PORT", "8081"))
    host = os.getenv("TOKEN_SERVER_HOST", "0.0.0.0")
    
    print(f"🚀 Starting Simple LiveKit Token Server...")
    print(f"📡 Binding to {host}:{port}")
    print(f"🔑 API Key: {LIVEKIT_API_KEY}")
    print(f"🔐 API Secret: {LIVEKIT_API_SECRET[:10]}...")
    
    try:
        server = HTTPServer((host, port), SimpleTokenHandler)
        print(f"✅ Token Server running on http://{host}:{port}")
        print(f"📝 Generate tokens: http://localhost:{port}/?room=myroom&participant=myuser")
        print(f"🛑 Press Ctrl+C to stop")
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        raise

if __name__ == "__main__":
    main()