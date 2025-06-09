"""
Core type definitions for the PyPolyCall library.

This module defines fundamental types used throughout the PyPolyCall system,
establishing a foundation for type safety and ensuring compatibility with
the LibPolyCall C library.
"""

from enum import IntEnum, IntFlag
from typing import Dict, Any, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass
import struct
import time

# Type definitions
CoreContext = TypeVar('CoreContext')
ProtocolContext = TypeVar('ProtocolContext')
StateContext = TypeVar('StateContext')


class CoreError(IntEnum):
    """Core error codes matching the LibPolyCall C definitions."""
    SUCCESS = 0
    INVALID_PARAMETERS = 1
    OUT_OF_MEMORY = 2
    INVALID_OPERATION = 3
    INVALID_STATE = 4
    INVALID_HANDLE = 5
    INVALID_TYPE = 6
    INVALID_TOKEN = 7
    INVALID_CONTEXT = 8
    ACCESS_DENIED = 9
    NOT_FOUND = 10
    UNAVAILABLE = 11
    UNAUTHORIZED = 12
    TIMEOUT = 13
    INITIALIZATION_FAILED = 14
    NOT_INITIALIZED = 15
    ALREADY_INITIALIZED = 16
    UNSUPPORTED_OPERATION = 17
    NOT_SUPPORTED = 18
    CANCELED = 19
    IO_ERROR = 20
    NETWORK = 21
    PROTOCOL = 22
    FILE_NOT_FOUND = 23
    FILE_OPERATION_FAILED = 24
    BUFFER_UNDERFLOW = 25
    BUFFER_OVERFLOW = 26
    TYPE_MISMATCH = 27
    VALIDATION_FAILED = 28
    SECURITY = 29
    INTERNAL = 30


class ErrorSeverity(IntEnum):
    """Error severity levels."""
    INFO = 0
    WARNING = 1
    ERROR = 2
    FATAL = 3


class ErrorSource(IntEnum):
    """Error source module identifiers."""
    CORE = 0
    MEMORY = 1
    CONTEXT = 2
    PROTOCOL = 3
    NETWORK = 4
    PARSER = 5
    MICRO = 6
    EDGE = 7
    CONFIG = 8
    USER = 0x1000  # Start of user-defined sources


class ContextType(IntEnum):
    """Context types."""
    CORE = 0
    PROTOCOL = 1
    NETWORK = 2
    MICRO = 3
    EDGE = 4
    PARSER = 5
    USER = 0x1000  # Start of user-defined context types


class ContextFlags(IntFlag):
    """Context flags."""
    NONE = 0
    INITIALIZED = 1 << 0
    LOCKED = 1 << 1
    SHARED = 1 << 2
    RESTRICTED = 1 << 3
    ISOLATED = 1 << 4


class ConfigSection(IntEnum):
    """Configuration section types."""
    CORE = 0
    SECURITY = 1
    MEMORY = 2
    TYPE = 3
    PERFORMANCE = 4
    PROTOCOL = 5
    C = 6
    JVM = 7
    JS = 8
    PYTHON = 9
    USER = 0x1000  # Start of user-defined sections


class ConfigValueType(IntEnum):
    """Configuration value types."""
    BOOLEAN = 0
    INTEGER = 1
    FLOAT = 2
    STRING = 3
    OBJECT = 4


class ProtocolState(IntEnum):
    """Protocol state enumeration."""
    INIT = 0
    HANDSHAKE = 1
    AUTH = 2
    READY = 3
    ERROR = 4
    CLOSED = 5


class MessageType(IntEnum):
    """Protocol message types."""
    HANDSHAKE = 0x01
    AUTH = 0x02
    COMMAND = 0x03
    RESPONSE = 0x04
    ERROR = 0x05
    HEARTBEAT = 0x06


class ProtocolFlags(IntFlag):
    """Protocol message flags."""
    NONE = 0x00
    SECURE = 1 << 0
    RELIABLE = 1 << 1
    ENCRYPTED = 1 << 2
    COMPRESSED = 1 << 3
    FRAGMENTED = 1 << 4
    LAST_FRAGMENT = 1 << 5


class PacketFlags(IntFlag):
    """Network packet flags."""
    NONE = 0
    ENCRYPTED = 1 << 0
    COMPRESSED = 1 << 1
    URGENT = 1 << 2
    RELIABLE = 1 << 3
    FRAGMENT = 1 << 4
    LAST_FRAGMENT = 1 << 5
    REQUIRES_ACK = 1 << 6
    IS_ACK = 1 << 7
    IS_SYSTEM = 1 << 8


class StateRelationship(IntEnum):
    """Hierarchical state relationship types."""
    PARENT = 0
    COMPOSITION = 1
    PARALLEL = 2


class PermissionInheritance(IntEnum):
    """Permission inheritance models."""
    NONE = 0
    ADDITIVE = 1
    SUBTRACTIVE = 2
    REPLACE = 3


class TransitionType(IntEnum):
    """Hierarchical state transition types."""
    LOCAL = 0
    EXTERNAL = 1
    INTERNAL = 2


@dataclass
class ErrorRecord:
    """Error record structure."""
    source: ErrorSource
    code: int
    severity: ErrorSeverity
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class MessageHeader:
    """Protocol message header."""
    version: int
    type: MessageType
    flags: ProtocolFlags
    sequence: int
    payload_length: int
    checksum: int

    def to_bytes(self) -> bytes:
        """Convert header to byte representation."""
        return struct.pack(
            "!BBHIII",
            self.version,
            self.type,
            self.flags,
            self.sequence,
            self.payload_length,
            self.checksum
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MessageHeader':
        """Create header from byte representation."""
        if len(data) < 16:
            raise ValueError("Header data too short")
        
        version, msg_type, flags, sequence, payload_length, checksum = struct.unpack(
            "!BBHIII", data[:16]
        )
        
        return cls(
            version=version,
            type=MessageType(msg_type),
            flags=ProtocolFlags(flags),
            sequence=sequence,
            payload_length=payload_length,
            checksum=checksum
        )


@dataclass
class PacketMetadata:
    """Packet metadata entry structure."""
    key: str
    value: Any
    value_size: int

    def __post_init__(self):
        if len(self.key) > 32:
            raise ValueError("Metadata key too long (max 32 characters)")


@dataclass
class NetworkPacket:
    """Network packet structure matching the C definition."""
    type: int
    id: int
    sequence: int
    timestamp: int
    flags: PacketFlags
    checksum: int
    priority: int
    
    data: bytes
    data_size: int
    buffer_capacity: int
    owns_data: bool
    
    metadata: Dict[str, PacketMetadata]

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}
        
        if len(self.metadata) > 16:
            raise ValueError("Too many metadata entries (max 16)")
        
        if self.data_size != len(self.data):
            self.data_size = len(self.data)
        
        if self.buffer_capacity < self.data_size:
            self.buffer_capacity = self.data_size


class PolyCallException(Exception):
    """Base exception for all PyPolyCall exceptions."""
    def __init__(self, code: CoreError, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code.name}] {message}")


class ProtocolException(PolyCallException):
    """Exception for protocol-related errors."""
    pass


class NetworkException(PolyCallException):
    """Exception for network-related errors."""
    pass


class StateException(PolyCallException):
    """Exception for state-related errors."""
    pass


class ConfigException(PolyCallException):
    """Exception for configuration-related errors."""
    pass