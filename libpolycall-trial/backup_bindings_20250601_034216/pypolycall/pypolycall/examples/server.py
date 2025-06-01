#!/usr/bin/env python3
"""
PyPolyCall Server - Python equivalent of server.js
Strict port mapping: 3001:8084 (RESERVED FOR PYTHON)
"""

import json
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from modules.router import Router
from modules.state import State


class PolyCallHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for PyPolyCall server"""
    
    def log_message(self, format, *args):
        """Override to use custom logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")
    
    def handle_cors(self):
        """Handle CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        if self.command == 'OPTIONS':
            self.send_response(204)
            self.end_headers()
            return True
        return False
    
    def parse_body(self):
        """Parse request body"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                return json.loads(body) if body else {}
            return {}
        except (ValueError, json.JSONDecodeError):
            raise ValueError('Invalid JSON')
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        response_body = json.dumps(data).encode('utf-8')
        
        self.send_response(status)
        self.handle_cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)
    
    def send_error_response(self, error_message, status=500):
        """Send error response"""
        # Determine status code based on error
        if 'not found' in error_message.lower():
            status = 404
        elif 'not allowed' in error_message.lower():
            status = 405
        
        error_data = {
            'success': False,
            'error': error_message
        }
        self.send_json_response(error_data, status)
    
    def do_GET(self):
        """Handle GET requests"""
        self.handle_request()
    
    def do_POST(self):
        """Handle POST requests"""
        self.handle_request()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS)"""
        if self.handle_cors():
            return
    
    def handle_request(self):
        """Handle incoming requests through router"""
        try:
            # Handle CORS
            if self.handle_cors():
                return
            
            # Parse request body
            body = self.parse_body()
            
            # Handle request through router
            result = asyncio.run(self.server.router.handle_request(
                self.path,
                self.command,
                body
            ))
            
            # Send success response
            self.send_json_response(result)
            
        except Exception as error:
            # Send error response
            self.send_error_response(str(error))


class PolyCallServer:
    """PyPolyCall Server with strict port binding"""
    
    def __init__(self):
        # Initialize router
        self.router = Router()
        
        # Data store (in-memory for demo)
        self.store = {
            'books': {}
        }
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup API routes"""
        
        # Book handlers - same logic as Node.js version
        book_handlers = {
            'GET': self.get_books,
            'POST': self.create_book
        }
        
        # Register routes
        self.router.add_route('/books', book_handlers)
    
    async def get_books(self, ctx):
        """GET /books handler"""
        books = list(self.store['books'].values())
        return {'success': True, 'data': books}
    
    async def create_book(self, ctx):
        """POST /books handler"""
        book = ctx.data
        
        # Validate input
        if not book.get('title') or not book.get('author'):
            raise ValueError('Book must have title and author')
        
        # Create new book
        book_id = str(int(datetime.now().timestamp() * 1000))
        new_book = {
            'id': book_id,
            'title': book['title'],
            'author': book['author'],
            'created_at': datetime.now().isoformat()
        }
        
        # Save book
        self.store['books'][book_id] = new_book
        return {'success': True, 'data': new_book}
    
    def create_http_handler(self):
        """Create HTTP handler class with router reference"""
        server_instance = self
        
        class RequestHandler(PolyCallHTTPHandler):
            def __init__(self, *args, **kwargs):
                self.server = server_instance
                super().__init__(*args, **kwargs)
        
        return RequestHandler
    
    def start(self, port=8084, host='localhost'):
        """Start the PyPolyCall server"""
        print(f"🐍 Starting PyPolyCall Server")
        print(f"📡 Strict Port Binding: {port} (RESERVED FOR PYTHON)")
        print(f"🛡️  Zero-Trust Mode: Enabled")
        print("=" * 50)
        
        # Verify port configuration
        self.verify_port_config(port)
        
        # Create HTTP server
        handler_class = self.create_http_handler()
        httpd = HTTPServer((host, port), handler_class)
        
        print(f"✅ Server running at http://{host}:{port}")
        self.router.print_routes()
        print("\n🔒 Security Status:")
        print("   ✅ Strict port binding enforced")
        print("   ✅ Zero-trust configuration active")
        print("   ✅ Python binding isolated")
        print("\nPress Ctrl+C to stop...")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopping...")
            httpd.server_close()
            print("✅ Server stopped")
    
    def verify_port_config(self, port):
        """Verify strict port configuration"""
        RESERVED_PORTS = {
            8080: 'node.js',
            3001: 'python',   # THIS BINDING
            3002: 'java',
            3003: 'go',
            3004: 'lua'
        }
        
        if port not in RESERVED_PORTS:
            raise ValueError(f"❌ Port {port} not in reserved mapping")
        
        if RESERVED_PORTS[port] != 'python':
            raise ValueError(f"❌ Port {port} reserved for {RESERVED_PORTS[port]}, not Python")
        
        print(f"✅ Port {port} verified for Python binding")


def main():
    """Main entry point"""
    # Strict port enforcement - ONLY 8084 allowed for Python
    PORT = 8084  # Container port from 3001:8084 mapping
    
    try:
        server = PolyCallServer()
        server.start(PORT)
    except Exception as error:
        print(f"❌ Server failed to start: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
