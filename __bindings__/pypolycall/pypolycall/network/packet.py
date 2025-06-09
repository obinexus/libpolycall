"""
Network packet implementation for PyPolyCall.

This module provides packet creation, serialization, and management
for the PyPolyCall network layer, ensuring compatibility with the
LibPolyCall C implementation.
"""

import struct
import time
import zlib
from typing import Dict, Optional, Any, Union, List
from dataclasses import dataclass, field

from ..core.types import PacketFlags, PacketMetadata, NetworkPacket, CoreError
from ..core.error import set_error, ErrorSource, check_params

# Packet constants
DEFAULT_PACKET_CAPACITY = 1024
PACKET_HEADER_SIZE = 24
MAX_METADATA_ENTRIES = 16


class PacketBuilder:
    """Builder for network packets."""
    
    def __init__(self, initial_capacity: int = DEFAULT_PACKET_CAPACITY):
        """
        Initialize a packet builder.
        
        Args:
            initial_capacity: Initial packet buffer capacity
        """
        self.type = 0
        self.id = 0
        self.sequence = 0
        self.timestamp = int(time.time() * 1000)
        self.flags = PacketFlags.NONE
        self.priority = 0
        self.metadata: Dict[str, PacketMetadata] = {}
        self.data = bytearray(initial_capacity)
        self.data_size = 0
        self.buffer_capacity = initial_capacity
    
    def set_type(self, packet_type: int) -> 'PacketBuilder':
        """
        Set packet type.
        
        Args:
            packet_type: Packet type
        
        Returns:
            Self for chaining
        """
        self.type = packet_type
        return self
    
    def set_id(self, packet_id: int) -> 'PacketBuilder':
        """
        Set packet ID.
        
        Args:
            packet_id: Packet ID
        
        Returns:
            Self for chaining
        """
        self.id = packet_id
        return self
    
    def set_sequence(self, sequence: int) -> 'PacketBuilder':
        """
        Set packet sequence number.
        
        Args:
            sequence: Sequence number
        
        Returns:
            Self for chaining
        """
        self.sequence = sequence
        return self
    
    def set_timestamp(self, timestamp: int) -> 'PacketBuilder':
        """
        Set packet timestamp.
        
        Args:
            timestamp: Timestamp (milliseconds since epoch)
        
        Returns:
            Self for chaining
        """
        self.timestamp = timestamp
        return self
    
    def set_flags(self, flags: PacketFlags) -> 'PacketBuilder':
        """
        Set packet flags.
        
        Args:
            flags: Packet flags
        
        Returns:
            Self for chaining
        """
        self.flags = flags
        return self
    
    def add_flag(self, flag: PacketFlags) -> 'PacketBuilder':
        """
        Add a packet flag.
        
        Args:
            flag: Packet flag to add
        
        Returns:
            Self for chaining
        """
        self.flags |= flag
        return self
    
    def set_priority(self, priority: int) -> 'PacketBuilder':
        """
        Set packet priority.
        
        Args:
            priority: Priority (0-255)
        
        Returns:
            Self for chaining
        """
        self.priority = max(0, min(255, priority))
        return self
    
    def set_data(self, data: Union[bytes, bytearray, str]) -> 'PacketBuilder':
        """
        Set packet data.
        
        Args:
            data: Packet data
        
        Returns:
            Self for chaining
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        data_size = len(data)
        
        # Resize buffer if needed
        if data_size > self.buffer_capacity:
            self.data = bytearray(data_size)
            self.buffer_capacity = data_size
        
        # Copy data
        self.data[:data_size] = data
        self.data_size = data_size
        
        return self
    
    def append_data(self, data: Union[bytes, bytearray, str]) -> 'PacketBuilder':
        """
        Append data to the packet.
        
        Args:
            data: Data to append
        
        Returns:
            Self for chaining
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        data_size = len(data)
        new_size = self.data_size + data_size
        
        # Resize buffer if needed
        if new_size > self.buffer_capacity:
            new_capacity = max(new_size, self.buffer_capacity * 2)
            new_buffer = bytearray(new_capacity)
            new_buffer[:self.data_size] = self.data[:self.data_size]
            self.data = new_buffer
            self.buffer_capacity = new_capacity
        
        # Append data
        self.data[self.data_size:new_size] = data
        self.data_size = new_size
        
        return self
    
    def add_metadata(self, key: str, value: Any, value_size: Optional[int] = None) -> 'PacketBuilder':
        """
        Add metadata to the packet.
        
        Args:
            key: Metadata key (max 32 characters)
            value: Metadata value
            value_size: Value size in bytes (auto-calculated if None)
        
        Returns:
            Self for chaining
        
        Raises:
            ValueError: If key is too long or too many metadata entries
        """
        if len(key) > 32:
            raise ValueError("Metadata key too long (max 32 characters)")
        
        if len(self.metadata) >= MAX_METADATA_ENTRIES:
            raise ValueError(f"Too many metadata entries (max {MAX_METADATA_ENTRIES})")
        
        # Calculate value size
        if value_size is None:
            if isinstance(value, (bytes, bytearray)):
                value_size = len(value)
            elif isinstance(value, str):
                value_size = len(value.encode('utf-8'))
            elif isinstance(value, (int, float, bool)):
                value_size = 8  # Fixed size for primitive types
            else:
                value_size = 0  # Unknown
        
        # Create metadata entry
        metadata = PacketMetadata(key=key, value=value, value_size=value_size)
        
        # Add to metadata
        self.metadata[key] = metadata
        
        return self
    
    def build(self) -> NetworkPacket:
        """
        Build a network packet.
        
        Returns:
            Network packet
        """
        # Calculate checksum
        checksum = zlib.crc32(bytes(self.data[:self.data_size])) & 0xFFFFFFFF
        
        return NetworkPacket(
            type=self.type,
            id=self.id,
            sequence=self.sequence,
            timestamp=self.timestamp,
            flags=self.flags,
            checksum=checksum,
            priority=self.priority,
            data=bytes(self.data[:self.data_size]),
            data_size=self.data_size,
            buffer_capacity=self.buffer_capacity,
            owns_data=True,
            metadata=self.metadata
        )


class PacketSerializer:
    """Serializer for network packets."""
    
    @staticmethod
    def serialize(packet: NetworkPacket) -> bytes:
        """
        Serialize a packet to bytes.
        
        Args:
            packet: Network packet
        
        Returns:
            Serialized packet data
        """
        # Create header
        header = struct.pack(
            "!HIIQIIB",
            packet.type,
            packet.id,
            packet.sequence,
            packet.timestamp,
            packet.flags,
            packet.checksum,
            packet.priority
        )
        
        # Create metadata section
        metadata_count = len(packet.metadata)
        metadata_section = bytearray(4 + metadata_count * 40)  # 4 for count, 40 per entry (max)
        
        # Write metadata count
        metadata_section[:4] = struct.pack("!I", metadata_count)
        
        # Write metadata entries
        offset = 4
        for key, meta in packet.metadata.items():
            # Write key (fixed 32 bytes)
            key_bytes = key.encode('utf-8')
            key_size = min(32, len(key_bytes))
            metadata_section[offset:offset+key_size] = key_bytes[:key_size]
            offset += 32
            
            # Write value size
            metadata_section[offset:offset+4] = struct.pack("!I", meta.value_size)
            offset += 4
            
            # Write value type (4 bytes)
            value_type = 0  # Default type
            if isinstance(meta.value, (bytes, bytearray)):
                value_type = 1
            elif isinstance(meta.value, str):
                value_type = 2
            elif isinstance(meta.value, int):
                value_type = 3
            elif isinstance(meta.value, float):
                value_type = 4
            elif isinstance(meta.value, bool):
                value_type = 5
            
            metadata_section[offset:offset+4] = struct.pack("!I", value_type)
            offset += 4
        
        # Trim metadata section to actual size
        metadata_section = metadata_section[:offset]
        
        # Calculate sizes
        header_size = len(header)
        metadata_size = len(metadata_section)
        total_size = header_size + metadata_size + packet.data_size
        
        # Create complete packet
        result = bytearray(total_size)
        result[:header_size] = header
        result[header_size:header_size+metadata_size] = metadata_section
        result[header_size+metadata_size:] = packet.data
        
        return bytes(result)
    
    @staticmethod
    def deserialize(data: bytes) -> NetworkPacket:
        """
        Deserialize bytes to a packet.
        
        Args:
            data: Serialized packet data
        
        Returns:
            Network packet
        
        Raises:
            ValueError: If data is invalid
        """
        if len(data) < PACKET_HEADER_SIZE:
            raise ValueError("Packet data too short")
        
        # Parse header
        header_format = "!HIIQIIB"
        header_size = struct.calcsize(header_format)
        
        packet_type, packet_id, sequence, timestamp, flags, checksum, priority = struct.unpack(
            header_format,
            data[:header_size]
        )
        
        # Parse metadata
        metadata_offset = header_size
        metadata_count = struct.unpack("!I", data[metadata_offset:metadata_offset+4])[0]
        metadata_offset += 4
        
        metadata: Dict[str, PacketMetadata] = {}
        
        for _ in range(metadata_count):
            # Read key
            key_bytes = data[metadata_offset:metadata_offset+32].split(b'\0', 1)[0]
            key = key_bytes.decode('utf-8')
            metadata_offset += 32
            
            # Read value size
            value_size = struct.unpack("!I", data[metadata_offset:metadata_offset+4])[0]
            metadata_offset += 4
            
            # Read value type
            value_type = struct.unpack("!I", data[metadata_offset:metadata_offset+4])[0]
            metadata_offset += 4
            
            # For now, just store a placeholder value
            metadata[key] = PacketMetadata(key=key, value=None, value_size=value_size)
        
        # Extract payload
        payload = data[metadata_offset:]
        
        # Create packet
        return NetworkPacket(
            type=packet_type,
            id=packet_id,
            sequence=sequence,
            timestamp=timestamp,
            flags=PacketFlags(flags),
            checksum=checksum,
            priority=priority,
            data=payload,
            data_size=len(payload),
            buffer_capacity=len(payload),
            owns_data=True,
            metadata=metadata
        )


def create_packet(
    packet_type: int = 0,
    data: Optional[Union[bytes, bytearray, str]] = None,
    sequence: int = 0,
    flags: PacketFlags = PacketFlags.NONE,
    priority: int = 0
) -> NetworkPacket:
    """
    Create a network packet.
    
    Args:
        packet_type: Packet type
        data: Packet data
        sequence: Sequence number
        flags: Packet flags
        priority: Priority
    
    Returns:
        Network packet
    """
    builder = PacketBuilder()
    
    builder.set_type(packet_type)
    builder.set_sequence(sequence)
    builder.set_flags(flags)
    builder.set_priority(priority)
    
    if data is not None:
        builder.set_data(data)
    
    return builder.build()


def clone_packet(packet: NetworkPacket) -> NetworkPacket:
    """
    Clone a network packet.
    
    Args:
        packet: Packet to clone
    
    Returns:
        Cloned packet
    """
    builder = PacketBuilder(packet.data_size)
    
    builder.set_type(packet.type)
    builder.set_id(packet.id)
    builder.set_sequence(packet.sequence)
    builder.set_timestamp(packet.timestamp)
    builder.set_flags(packet.flags)
    builder.set_priority(packet.priority)
    builder.set_data(packet.data)
    
    # Clone metadata
    for key, meta in packet.metadata.items():
        builder.add_metadata(key, meta.value, meta.value_size)
    
    return builder.build()


def packet_to_bytes(packet: NetworkPacket) -> bytes:
    """
    Convert a packet to bytes.
    
    Args:
        packet: Network packet
    
    Returns:
        Serialized packet
    """
    return PacketSerializer.serialize(packet)


def bytes_to_packet(data: bytes) -> NetworkPacket:
    """
    Convert bytes to a packet.
    
    Args:
        data: Serialized packet data
    
    Returns:
        Network packet
    """
    return PacketSerializer.deserialize(data)


def verify_packet_checksum(packet: NetworkPacket) -> bool:
    """
    Verify packet checksum.
    
    Args:
        packet: Network packet
    
    Returns:
        True if checksum is valid, False otherwise
    """
    calculated = zlib.crc32(packet.data) & 0xFFFFFFFF
    return calculated == packet.checksum