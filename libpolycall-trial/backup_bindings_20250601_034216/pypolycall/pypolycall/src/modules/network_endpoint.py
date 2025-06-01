# network_endpoint.py - PyPolyCall Network Endpoint Implementation
import socket
import asyncio
from typing import Optional, Dict, Any

class NetworkEndpoint:
    """PyPolyCall Network Endpoint - Python equivalent of NetworkEndpoint.js"""
    
    def __init__(self, options: Dict[str, Any] = None):
        if options is None:
            options = {}
            
        self.options = {
            'host': 'localhost',
            'port': 8084,
            'backlog': 1024,
            'timeout': 5000,
            'keep_alive': True,
            'reconnect': True,
            'max_retries': 3,
            'retry_delay': 1000,
            **options
        }
        
        self.socket: Optional[socket.socket] = None
        self.server: Optional[socket.socket] = None
        self.connected = False
        self.retry_count = 0
        self.pending_data = []
    
    async def listen(self):
        """Start listening for connections"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.options['host'], self.options['port']))
        self.server.listen(self.options['backlog'])
        
        print(f"🔌 NetworkEndpoint listening on {self.options['host']}:{self.options['port']}")
        return self
    
    async def connect(self):
        """Connect to remote endpoint"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.socket.connect((self.options['host'], self.options['port']))
            self.connected = True
            self.retry_count = 0
            return self
        except Exception as error:
            self.connected = False
            raise error
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    def get_address(self) -> Optional[Dict[str, Any]]:
        """Get endpoint address"""
        if self.server:
            return {
                'host': self.options['host'],
                'port': self.options['port']
            }
        return None
    
    def __str__(self) -> str:
        address = self.get_address()
        if address:
            return f"NetworkEndpoint({address['host']}:{address['port']})"
        return "NetworkEndpoint(not connected)"
