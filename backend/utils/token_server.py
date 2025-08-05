#!/usr/bin/env python3
"""
Simple HTTP server for generating LiveKit tokens
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import jwt
import time
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# LiveKit dev server configuration
LIVEKIT_API_KEY = "devkey"
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "your_secret_key_at_least_32_characters_long")

def generate_livekit_token(room_name: str = None, participant_name: str = None, duration_hours: int = 24):
    """Generate a LiveKit JWT token."""
    
    if not room_name:
        room_name = f"voice-assistant-{int(time.time())}"
    
    if not participant_name:
        participant_name = f"user-{uuid.uuid4().hex[:8]}"
    
    now = datetime.now()
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
    
    token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
    
    return {
        "token": token,
        "room": room_name,
        "participant": participant_name,
        "expires": exp.isoformat()
    }

class TokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for token generation."""
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            room_name = query_params.get('room', [None])[0]
            participant_name = query_params.get('participant', [None])[0]
            
            # Generate token
            token_data = generate_livekit_token(room_name, participant_name)
            
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
            
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = json.dumps({"error": str(e)})
            self.wfile.write(error_response.encode())
    
    def log_message(self, format, *args):
        """Override to log messages to stdout"""
        print(f"[{self.log_date_time_string()}] {format % args}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    """Start the token server."""
    port = 8081
    print(f"🚀 Starting LiveKit Token Server...")
    print(f"📡 Binding to 0.0.0.0:{port}")
    
    try:
        server = HTTPServer(('0.0.0.0', port), TokenHandler)
        print(f"✅ LiveKit Token Server running on http://0.0.0.0:{port}")
        print(f"📝 Generate tokens: http://localhost:{port}/?room=myroom&participant=myuser")
        print(f"🛑 Press Ctrl+C to stop")
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        raise
        server.server_close()

if __name__ == "__main__":
    main() 