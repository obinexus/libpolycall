# polycall_client.py - PyPolyCall Client Implementation
import asyncio
from typing import Dict, Any, Optional
from .network_endpoint import NetworkEndpoint
from .router import Router
from .state_machine import StateMachine

class PolyCallClient:
    """PyPolyCall Client - Python equivalent of PolyCallClient.js"""
    
    def __init__(self, options: Dict[str, Any] = None):
        if options is None:
            options = {}
            
        self.options = {
            'host': 'localhost',
            'port': 8084,  # Python binding uses 8084 (container port)
            'reconnect': True,
            'timeout': 5000,
            'max_retries': 3,
            **options
        }
        
        # Core components
        self.endpoint = NetworkEndpoint(self.options)
        self.router = Router()
        self.state_machine = StateMachine(self.options)
        
        # Internal state
        self.connected = False
        self.authenticated = False
        self.pending_requests = {}
    
    async def connect(self):
        """Connect to LibPolyCall server"""
        try:
            await self.endpoint.connect()
            self.connected = True
            print(f"✅ Connected to LibPolyCall server on port {self.options['port']}")
            return True
        except Exception as error:
            print(f"❌ Connection failed: {error}")
            raise error
    
    async def disconnect(self):
        """Disconnect from server"""
        try:
            self.connected = False
            self.authenticated = False
            print("🔌 Disconnected from LibPolyCall server")
        except Exception as error:
            raise error
    
    async def send_request(self, path: str, method: str = 'GET', data: Dict[str, Any] = None):
        """Send request through router"""
        if not self.connected:
            raise RuntimeError('Not connected to server')
        
        if data is None:
            data = {}
            
        try:
            response = await self.router.handle_request(path, method, data)
            return response
        except Exception as error:
            raise error
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self.authenticated
    
    def __str__(self) -> str:
        return f"PolyCallClient({self.endpoint})"
