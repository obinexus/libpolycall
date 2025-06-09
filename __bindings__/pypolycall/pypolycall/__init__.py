"""
PyPolyCall - Python bindings for LibPolyCall.

This package provides Python bindings for the LibPolyCall library,
implementing a "program-first" design for cross-language communication.
"""

import logging
from typing import Dict, Any, Optional

from .core.types import (
    CoreError, 
    ErrorSource, 
    ErrorSeverity,
    MessageType, 
    ProtocolState, 
    ProtocolFlags,
    PacketFlags
)
from .core.error import PolyCallException
from .client.polycall_client import PolyCallClient

# Package version
__version__ = "0.1.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def create_client(options: Optional[Dict[str, Any]] = None) -> PolyCallClient:
    """
    Create a PolyCall client.
    
    Args:
        options: Client options
    
    Returns:
        PolyCall client instance
    """
    return PolyCallClient(options)


# Export public classes and functions
__all__ = [
    # Version
    "__version__",
    
    # Client
    "PolyCallClient",
    "create_client",
    
    # Core types
    "CoreError",
    "ErrorSource",
    "ErrorSeverity",
    "MessageType",
    "ProtocolState",
    "ProtocolFlags",
    "PacketFlags",
    
    # Exceptions
    "PolyCallException"
]