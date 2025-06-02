"""
PyPolyCall Module - LibPolyCall Python Binding
Professional implementation with systematic module discovery
Generated: 2025-06-01T04:02:05.512681
"""

import sys
import os
from pathlib import Path

# Establish module path resolution
PYPOLYCALL_ROOT = Path(__file__).parent
MODULES_PATH = PYPOLYCALL_ROOT / "src" / "modules"
BINDING_PATH = PYPOLYCALL_ROOT.parent.parent

# Add paths to Python path for proper module discovery
if str(MODULES_PATH) not in sys.path:
    sys.path.insert(0, str(MODULES_PATH))

if str(BINDING_PATH) not in sys.path:
    sys.path.insert(0, str(BINDING_PATH))

# Export core components for binding ecosystem
try:
    from modules.polycall_client import PolyCallClient
    from modules.router import Router
    from modules.state_machine import StateMachine
    from modules.protocol_handler import ProtocolHandler
    from modules.network_endpoint import NetworkEndpoint
    
    __all__ = [
        'PolyCallClient',
        'Router', 
        'StateMachine',
        'ProtocolHandler',
        'NetworkEndpoint'
    ]
    
    # Verify module resolution
    MODULES_DISCOVERED = True
    
except ImportError as e:
    print(f"PyPolyCall Module Discovery Warning: {e}")
    MODULES_DISCOVERED = False
    __all__ = []

# Binding configuration
BINDING_CONFIG = {
    "binding_type": "python-polycall",
    "version": "1.0.0",
    "port_mapping": "3001:444",
    "modules_discovered": MODULES_DISCOVERED,
    "discovery_path": str(MODULES_PATH),
    "libpolycall_integration": True
}

def get_binding_info():
    """Return comprehensive binding information for diagnostics"""
    return {
        "binding_config": BINDING_CONFIG,
        "module_paths": {
            "pypolycall_root": str(PYPOLYCALL_ROOT),
            "modules_path": str(MODULES_PATH),
            "binding_path": str(BINDING_PATH)
        },
        "discovered_modules": __all__,
        "python_path": sys.path[:5],  # First 5 entries for relevance
        "discovery_status": MODULES_DISCOVERED
    }

def verify_libpolycall_integration():
    """Verify LibPolyCall core integration capability"""
    try:
        # Test basic module imports
        if MODULES_DISCOVERED:
            client = PolyCallClient(host='localhost', port=444)
            return {
                "integration_status": "operational",
                "client_initialized": True,
                "binding_ready": True
            }
        else:
            return {
                "integration_status": "module_discovery_failed", 
                "client_initialized": False,
                "binding_ready": False
            }
    except Exception as e:
        return {
            "integration_status": "error",
            "error_message": str(e),
            "binding_ready": False
        }
