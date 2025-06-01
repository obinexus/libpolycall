# protocol_handler.py - PyPolyCall Protocol Handler Implementation
import hashlib
import json
from typing import Dict, Any, Optional

class ProtocolHandler:
    """PyPolyCall Protocol Handler - Python equivalent of ProtocolHandler.js"""
    
    PROTOCOL_CONSTANTS = {
        'VERSION': 1,
        'MAGIC': 0x504C43,  # "PLC"
        'HEADER_SIZE': 16,
        'MAX_PAYLOAD_SIZE': 1024 * 1024,  # 1MB
        'DEFAULT_TIMEOUT': 5000
    }
    
    MESSAGE_TYPES = {
        'HANDSHAKE': 0x01,
        'AUTH': 0x02,
        'COMMAND': 0x03,
        'RESPONSE': 0x04,
        'ERROR': 0x05,
        'HEARTBEAT': 0x06
    }
    
    PROTOCOL_FLAGS = {
        'NONE': 0x00,
        'ENCRYPTED': 0x01,
        'COMPRESSED': 0x02,
        'URGENT': 0x04,
        'RELIABLE': 0x08
    }
    
    def __init__(self, options: Dict[str, Any] = None):
        if options is None:
            options = {}
            
        self.version = options.get('version', self.PROTOCOL_CONSTANTS['VERSION'])
        self.checksum_algorithm = options.get('checksum_algorithm', 'sha256')
        self.sequence = 1
        self.pending_messages = {}
        self.encryption_enabled = options.get('encryption', False)
        self.compression_enabled = options.get('compression', False)
    
    def create_header(self, msg_type: int, payload_length: int, flags: int = 0) -> bytes:
        """Create protocol header"""
        header = bytearray(self.PROTOCOL_CONSTANTS['HEADER_SIZE'])
        
        # Pack header fields
        header[0] = self.version
        header[1] = msg_type
        header[2:4] = flags.to_bytes(2, 'little')
        header[4:8] = self.sequence.to_bytes(4, 'little')
        header[8:12] = payload_length.to_bytes(4, 'little')
        header[12:16] = (0).to_bytes(4, 'little')  # Checksum placeholder
        
        self.sequence += 1
        return bytes(header)
    
    def calculate_checksum(self, data: bytes) -> int:
        """Calculate checksum for data"""
        checksum = 0
        for byte in data:
            checksum = ((checksum << 5) | (checksum >> 27)) + byte
        return checksum & 0xFFFFFFFF
    
    def create_message(self, msg_type: int, payload: bytes, flags: int = 0) -> bytes:
        """Create complete protocol message"""
        header = self.create_header(msg_type, len(payload), flags)
        checksum = self.calculate_checksum(payload)
        
        # Update checksum in header
        header_array = bytearray(header)
        header_array[12:16] = checksum.to_bytes(4, 'little')
        
        return bytes(header_array) + payload
    
    def verify_message(self, data: bytes) -> bool:
        """Verify message integrity"""
        if len(data) < self.PROTOCOL_CONSTANTS['HEADER_SIZE']:
            return False
            
        header = data[:self.PROTOCOL_CONSTANTS['HEADER_SIZE']]
        payload = data[self.PROTOCOL_CONSTANTS['HEADER_SIZE']:]
        
        # Extract checksum from header
        stored_checksum = int.from_bytes(header[12:16], 'little')
        calculated_checksum = self.calculate_checksum(payload)
        
        return stored_checksum == calculated_checksum
