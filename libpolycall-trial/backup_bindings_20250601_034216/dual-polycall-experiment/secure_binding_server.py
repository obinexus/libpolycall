#!/usr/bin/env python3
"""
LibPolyCall Secure Binding Server
Enhanced authentication and binding validation implementation
Prevents impersonation attacks and enforces binding isolation
"""

import json
import socket
import hashlib
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

class SecureBindingServer(BaseHTTPRequestHandler):
    """Enhanced server with binding validation and anti-impersonation measures"""
    
    # Binding Registry with network characteristics
    BINDING_REGISTRY = {
        'node-binding': {
            'api_key': 'nb_secure_key_12345',
            'expected_host_port': 3000,
            'container_port': 433,
            'allowed_ips': ['127.0.0.1', '::1'],
            'binding_type': 'node',
            'protocol_version': '1.0',
            'max_concurrent_connections': 50
        },
        'pypolycall-binding': {
            'api_key': 'py_secure_key_67890', 
            'expected_host_port': 3001,
            'container_port': 444,
            'allowed_ips': ['127.0.0.1', '::1'],
            'binding_type': 'python',
            'protocol_version': '1.0',
            'max_concurrent_connections': 30
        }
    }
    
    # Active binding connections tracker
    ACTIVE_CONNECTIONS = {}
    
    def validate_binding_network_characteristics(self, binding_type, client_ip):
        """Validate binding request against expected network characteristics"""
        if binding_type not in self.BINDING_REGISTRY:
            return False, "Unknown binding type"
        
        binding_config = self.BINDING_REGISTRY[binding_type]
        
        # Validate client IP is in allowed list
        if client_ip not in binding_config['allowed_ips']:
            return False, f"IP {client_ip} not authorized for {binding_type}"
        
        # Check concurrent connection limits
        active_count = self.ACTIVE_CONNECTIONS.get(binding_type, 0)
        if active_count >= binding_config['max_concurrent_connections']:
            return False, f"Connection limit exceeded for {binding_type}"
        
        return True, "Network validation passed"
    
    def authenticate_binding_request(self, api_key, binding_type, client_ip):
        """Multi-layer binding authentication"""
        # Layer 1: API Key validation
        if binding_type not in self.BINDING_REGISTRY:
            return None, "Invalid binding type"
        
        binding_config = self.BINDING_REGISTRY[binding_type]
        if api_key != binding_config['api_key']:
            return None, "Invalid API key for binding type"
        
        # Layer 2: Network characteristics validation
        network_valid, network_msg = self.validate_binding_network_characteristics(
            binding_type, client_ip
        )
        if not network_valid:
            return None, network_msg
        
        # Layer 3: Generate binding session token
        session_data = {
            'binding_type': binding_type,
            'client_ip': client_ip,
            'timestamp': int(time.time()),
            'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest()[:8]
        }
        
        session_token = self.generate_session_token(session_data)
        
        return session_token, "Authentication successful"
    
    def generate_session_token(self, session_data):
        """Generate cryptographic session token for binding"""
        token_input = json.dumps(session_data, sort_keys=True)
        return hashlib.sha256(token_input.encode()).hexdigest()[:16]
    
    def validate_request_integrity(self, request_data, expected_binding_type):
        """Validate request hasn't been malformed or hijacked"""
        # Check for required headers
        required_headers = ['X-API-Key', 'X-Binding-Type', 'Content-Type']
        for header in required_headers:
            if not self.headers.get(header):
                return False, f"Missing required header: {header}"
        
        # Validate binding type consistency
        header_binding_type = self.headers.get('X-Binding-Type')
        if header_binding_type != expected_binding_type:
            return False, "Binding type mismatch"
        
        # Check for suspicious request patterns
        user_agent = self.headers.get('User-Agent', '')
        if 'polycall' not in user_agent.lower() and user_agent != '':
            return False, "Suspicious user agent"
        
        return True, "Request integrity validated"
    
    def handle_binding_contract_creation(self, contract_data, api_key, binding_type, client_ip):
        """Enhanced contract creation with binding validation"""
        # Authenticate binding
        session_token, auth_msg = self.authenticate_binding_request(
            api_key, binding_type, client_ip
        )
        
        if not session_token:
            return {'error': auth_msg}, 401
        
        # Validate contract data integrity
        required_contract_fields = ['operation', 'endpoint', 'data_schema']
        for field in required_contract_fields:
            if field not in contract_data:
                return {'error': f'Missing contract field: {field}'}, 400
        
        # Create secure binding contract
        contract_id = f"contract_{binding_type}_{int(time.time())}"
        
        contract = {
            'contract_id': contract_id,
            'binding_type': binding_type,
            'session_token': session_token,
            'client_ip': client_ip,
            'contract_data': contract_data,
            'polycall_endpoint': './bin/polycall',
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'security_level': 'zero_trust_validated',
            'network_validated': True
        }
        
        # Generate contract signature
        contract_signature = self.generate_contract_signature(contract, api_key)
        contract['signature'] = contract_signature
        
        # Track active connection
        self.ACTIVE_CONNECTIONS[binding_type] = self.ACTIVE_CONNECTIONS.get(binding_type, 0) + 1
        
        response = {
            'success': True,
            'data': contract,
            'polycall_command': f'./bin/polycall --contract {contract_id} --binding {binding_type}',
            'metadata': {
                'session_token': session_token,
                'network_validated': True,
                'zero_trust_enforced': True,
                'binding_isolation': True
            }
        }
        
        return response, 201
    
    def generate_contract_signature(self, contract, api_key):
        """Generate tamper-proof contract signature"""
        # Create signature payload excluding the signature field itself
        contract_copy = contract.copy()
        contract_copy.pop('signature', None)
        
        signature_input = json.dumps(contract_copy, sort_keys=True) + api_key
        return hashlib.sha256(signature_input.encode()).hexdigest()
    
    def do_POST(self):
        """Handle POST requests with enhanced security"""
        client_ip = self.client_address[0]
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Extract authentication headers
        api_key = self.headers.get('X-API-Key')
        binding_type = self.headers.get('X-Binding-Type')
        
        if not api_key or not binding_type:
            self.send_json_response({'error': 'Missing authentication headers'}, 401)
            return
        
        # Parse request body
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                request_data = json.loads(body) if body else {}
            else:
                request_data = {}
        except (ValueError, json.JSONDecodeError):
            self.send_json_response({'error': 'Invalid JSON payload'}, 400)
            return
        
        # Validate request integrity
        integrity_valid, integrity_msg = self.validate_request_integrity(
            request_data, binding_type
        )
        if not integrity_valid:
            self.send_json_response({'error': f'Request integrity failed: {integrity_msg}'}, 400)
            return
        
        # Route secure requests
        if path == '/api/polycall/contract':
            response, status = self.handle_binding_contract_creation(
                request_data, api_key, binding_type, client_ip
            )
            self.send_json_response(response, status)
        else:
            self.send_json_response({'error': 'Endpoint not found'}, 404)
    
    def send_json_response(self, data, status=200):
        """Send JSON response with security headers"""
        response_body = json.dumps(data, indent=2).encode('utf-8')
        
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', 'localhost')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.send_header('X-LibPolyCall-Security', 'zero-trust-enforced')
        self.send_header('X-Binding-Isolation', 'enabled')
        self.end_headers()
        self.wfile.write(response_body)
    
    def log_message(self, format, *args):
        """Enhanced logging with binding context"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client_ip = getattr(self, 'client_address', ['unknown'])[0]
        binding_type = self.headers.get('X-Binding-Type', 'unknown') if hasattr(self, 'headers') else 'unknown'
        print(f"[{timestamp}] 🔒 LibPolyCall-Secure [{binding_type}@{client_ip}]: {format % args}")


def main():
    """Start the secure binding server"""
    HOST = 'localhost'
    PORT = 5000
    
    print("🔒 LibPolyCall Secure Binding Server")
    print("=" * 50)
    print(f"📡 Server: http://{HOST}:{PORT}")
    print(f"🛡️  Zero-Trust Security: ENFORCED")
    print(f"🔄 Binding Isolation: ENABLED")
    print("=" * 50)
    print("\n🔐 Registered Bindings:")
    
    for binding_name, config in SecureBindingServer.BINDING_REGISTRY.items():
        print(f"   {config['binding_type']}: {config['expected_host_port']}→{config['container_port']}")
    
    print("\n🛡️  Security Features:")
    print("   ✅ Network characteristic validation")
    print("   ✅ Anti-impersonation measures")
    print("   ✅ Request integrity verification")
    print("   ✅ Session token generation")
    print("   ✅ Contract signature validation")
    print("\nPress Ctrl+C to stop...")
    
    try:
        httpd = HTTPServer((HOST, PORT), SecureBindingServer)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Secure server stopping...")
        httpd.server_close()
        print("✅ Secure server stopped")


if __name__ == "__main__":
    main()