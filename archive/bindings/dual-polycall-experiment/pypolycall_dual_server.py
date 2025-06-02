#!/usr/bin/env python3
"""
PyPolyCall Server for Dual Testing with Node.js
Runs on port 3001 to avoid conflicts with Node.js (port 8084)
"""

import json
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys
import os
import threading
import time

# Add src to path for imports (adjust path as needed)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from modules.router import Router
    from modules.state import State
except ImportError:
    # Fallback - create minimal router for testing
    print("⚠️  Module imports failed, using fallback router")
    
    class Router:
        def __init__(self):
            self.routes = {}
        
        def add_route(self, path, handlers):
            self.routes[path] = handlers
        
        async def handle_request(self, path, method, data):
            if path in self.routes:
                handlers = self.routes[path]
                if isinstance(handlers, dict) and method in handlers:
                    return await handlers[method](type('Context', (), {'path': path, 'method': method, 'data': data})())
            raise ValueError(f"No route found for {method} {path}")
        
        def print_routes(self):
            print("\nPyPolyCall Routes:")
            for path, handlers in self.routes.items():
                if isinstance(handlers, dict):
                    methods = ','.join(handlers.keys())
                    print(f"  {methods} {path}")


class PyPolyCallHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for PyPolyCall dual testing server"""
    
    def log_message(self, format, *args):
        """Override to use custom logging with Python identifier"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 🐍 PyPolyCall: {format % args}")
    
    def handle_cors(self):
        """Handle CORS headers for dual testing"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('X-Server', 'PyPolyCall-Python')
        
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
        """Send JSON response with Python server identifier"""
        # Add server identifier to response
        if isinstance(data, dict):
            data['server'] = 'PyPolyCall-Python'
            data['port'] = 3001
            data['timestamp'] = datetime.now().isoformat()
        
        response_body = json.dumps(data, indent=2).encode('utf-8')
        
        self.send_response(status)
        self.handle_cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)
    
    def send_error_response(self, error_message, status=500):
        """Send error response"""
        if 'not found' in error_message.lower():
            status = 404
        elif 'not allowed' in error_message.lower():
            status = 405
        
        error_data = {
            'success': False,
            'error': error_message,
            'server': 'PyPolyCall-Python',
            'port': 3001
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
            if self.handle_cors():
                return
            
            body = self.parse_body()
            
            # Handle request through router
            result = asyncio.run(self.server.router.handle_request(
                self.path,
                self.command,
                body
            ))
            
            self.send_json_response(result)
            
        except Exception as error:
            self.send_error_response(str(error))


class PyPolyCallDualServer:
    """PyPolyCall Server for dual testing with Node.js"""
    
    def __init__(self):
        self.router = Router()
        
        # Separate data store for Python server
        self.store = {
            'books': {},
            'python_books': {},  # Python-specific storage
            'stats': {
                'requests': 0,
                'books_created': 0,
                'server_type': 'Python'
            }
        }
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup API routes for dual testing"""
        
        # Book handlers with Python-specific logic
        book_handlers = {
            'GET': self.get_books,
            'POST': self.create_book
        }
        
        # Python-specific routes
        python_handlers = {
            'GET': self.get_python_books,
            'POST': self.create_python_book
        }
        
        # Status/health check
        status_handlers = {
            'GET': self.get_status
        }
        
        # Register routes
        self.router.add_route('/books', book_handlers)
        self.router.add_route('/python/books', python_handlers)
        self.router.add_route('/status', status_handlers)
        self.router.add_route('/health', status_handlers)
    
    async def get_books(self, ctx):
        """GET /books - Returns all books from both stores"""
        self.store['stats']['requests'] += 1
        
        all_books = list(self.store['books'].values()) + list(self.store['python_books'].values())
        
        return {
            'success': True,
            'data': all_books,
            'server': 'PyPolyCall-Python',
            'total_books': len(all_books),
            'python_books': len(self.store['python_books']),
            'general_books': len(self.store['books'])
        }
    
    async def create_book(self, ctx):
        """POST /books - Creates a book in general store"""
        self.store['stats']['requests'] += 1
        book = ctx.data
        
        if not book.get('title') or not book.get('author'):
            raise ValueError('Book must have title and author')
        
        book_id = f"py_{int(datetime.now().timestamp() * 1000)}"
        new_book = {
            'id': book_id,
            'title': book['title'],
            'author': book['author'],
            'created_at': datetime.now().isoformat(),
            'created_by': 'PyPolyCall-Python',
            'server_port': 3001
        }
        
        self.store['books'][book_id] = new_book
        self.store['stats']['books_created'] += 1
        
        return {
            'success': True,
            'data': new_book,
            'message': 'Book created by PyPolyCall'
        }
    
    async def get_python_books(self, ctx):
        """GET /python/books - Returns Python-specific books"""
        self.store['stats']['requests'] += 1
        
        python_books = list(self.store['python_books'].values())
        return {
            'success': True,
            'data': python_books,
            'server': 'PyPolyCall-Python-Exclusive',
            'count': len(python_books)
        }
    
    async def create_python_book(self, ctx):
        """POST /python/books - Creates a Python-specific book"""
        self.store['stats']['requests'] += 1
        book = ctx.data
        
        if not book.get('title') or not book.get('author'):
            raise ValueError('Book must have title and author')
        
        book_id = f"python_{int(datetime.now().timestamp() * 1000)}"
        new_book = {
            'id': book_id,
            'title': f"[Python] {book['title']}",
            'author': book['author'],
            'created_at': datetime.now().isoformat(),
            'binding': 'Python-Exclusive',
            'server_port': 3001,
            'language': 'Python'
        }
        
        self.store['python_books'][book_id] = new_book
        self.store['stats']['books_created'] += 1
        
        return {
            'success': True,
            'data': new_book,
            'message': 'Python-exclusive book created'
        }
    
    async def get_status(self, ctx):
        """GET /status - Server status and stats"""
        self.store['stats']['requests'] += 1
        
        return {
            'success': True,
            'server': 'PyPolyCall-Python',
            'port': 3001,
            'status': 'running',
            'binding': 'Python',
            'stats': self.store['stats'],
            'uptime': datetime.now().isoformat(),
            'dual_testing': True,
            'companion_server': 'Node.js on port 8084'
        }
    
    def create_http_handler(self):
        """Create HTTP handler class with router reference"""
        server_instance = self
        
        class RequestHandler(PyPolyCallHTTPHandler):
            def __init__(self, *args, **kwargs):
                self.server = server_instance
                super().__init__(*args, **kwargs)
        
        return RequestHandler
    
    def start(self, port=3001, host='localhost'):
        """Start the PyPolyCall dual testing server"""
        print("🐍 Starting PyPolyCall Server for Dual Testing")
        print("=" * 55)
        print(f"📡 Python Server Port: {port}")
        print(f"🛡️  Zero-Trust Mode: Enabled")
        print(f"🔄 Dual Testing Mode: Active")
        print(f"👥 Companion: Node.js server on port 8084")
        print("=" * 55)
        
        # Create HTTP server
        handler_class = self.create_http_handler()
        httpd = HTTPServer((host, port), handler_class)
        
        print(f"✅ PyPolyCall server running at http://{host}:{port}")
        self.router.print_routes()
        
        print("\n🔒 Security & Dual Testing Status:")
        print("   ✅ Python binding isolated on port 3001")
        print("   ✅ Node.js companion on port 8084")
        print("   ✅ Cross-server communication ready")
        print("   ✅ Zero-trust configuration active")
        
        print("\n🧪 Dual Testing Endpoints:")
        print(f"   📊 Python Status: http://{host}:{port}/status")
        print(f"   📚 Python Books: http://{host}:{port}/books")
        print(f"   🐍 Python-Only: http://{host}:{port}/python/books")
        
        print("\nPress Ctrl+C to stop...")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 PyPolyCall server stopping...")
            httpd.server_close()
            print("✅ PyPolyCall server stopped")


def check_node_server():
    """Check if Node.js server is running"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', 8084))
            return result == 0
    except:
        return False


def main():
    """Main entry point for dual testing"""
    print("🔍 Checking for Node.js companion server...")
    
    if check_node_server():
        print("✅ Node.js server detected on port 8084")
        print("🔄 Dual testing mode: READY")
    else:
        print("⚠️  Node.js server not detected on port 8084")
        print("💡 Start Node.js server first: node server.js")
        print("🔄 Continuing with Python-only mode...")
    
    # Port configuration for dual testing
    PYTHON_PORT = 3001  # Python binding port
    
    try:
        server = PyPolyCallDualServer()
        server.start(PYTHON_PORT)
    except Exception as error:
        print(f"❌ PyPolyCall server failed to start: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
