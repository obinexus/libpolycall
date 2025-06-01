"""
PyPolyCall - Python Binding for LibPolyCall
Official Python binding with strict port mapping and zero-trust security
"""

__version__ = "1.0.0"
__author__ = "OBINexusComputing"
__license__ = "MIT"

# Import core modules
from .modules.router import Router
from .modules.state import State
from .modules.polycall_client import PolyCallClient
from .modules.state_machine import StateMachine
from .modules.network_endpoint import NetworkEndpoint
from .modules.protocol_handler import ProtocolHandler

# Package configuration
PACKAGE_CONFIG = {
    'name': 'pypolycall',
    'version': __version__,
    'binding_type': 'python',
    'reserved_ports': {
        'host': 3001,
        'container': 8084
    },
    'config_file': 'python.polycallrc',
    'zero_trust': True,
    'strict_binding': True
}

# Export public API
__all__ = [
    'Router',
    'State', 
    'PolyCallClient',
    'StateMachine',
    'NetworkEndpoint',
    'ProtocolHandler',
    'PACKAGE_CONFIG'
]

# Verify port configuration on import
def _verify_port_config():
    """Verify port configuration is not conflicting"""
    import os
    
    # Reserved port mappings (read-only)
    RESERVED_MAPPINGS = {
        'node': '8080:8084',
        'python': '3001:8084',  # THIS BINDING
        'java': '3002:8082',
        'go': '3003:8083',
        'lua': '3004:8085'
    }
    
    # Check if config file exists
    config_paths = [
        '/opt/polycall/services/python/python.polycallrc',
        './python.polycallrc',
        os.path.join(os.path.dirname(__file__), '..', 'python.polycallrc')
    ]
    
    config_found = False
    for path in config_paths:
        if os.path.exists(path):
            config_found = True
            break
    
    if not config_found:
        import warnings
        warnings.warn(
            "⚠️  PyPolyCall configuration not found. "
            "Please configure python.polycallrc with port mapping 3001:8084",
            UserWarning
        )

# Run verification on import
_verify_port_config()

def get_package_info():
    """Get package information"""
    return {
        'name': 'PyPolyCall',
        'version': __version__,
        'description': 'Python binding for LibPolyCall with strict port mapping',
        'author': __author__,
        'license': __license__,
        'binding_config': PACKAGE_CONFIG,
        'port_mapping': '3001:8084 (RESERVED FOR PYTHON)',
        'zero_trust': True
    }

def print_package_info():
    """Print package information"""
    info = get_package_info()
    print(f"\n🐍 {info['name']} v{info['version']}")
    print(f"📡 Port Mapping: {info['port_mapping']}")
    print(f"🛡️  Zero-Trust: {'Enabled' if info['zero_trust'] else 'Disabled'}")
    print(f"📄 License: {info['license']}")
    print(f"👤 Author: {info['author']}")

# Configuration validation functions
def validate_config():
    """Validate PyPolyCall configuration"""
    try:
        from .modules.polycall_config import PolyCallConfig
        config = PolyCallConfig()
        
        # Verify port mapping
        expected_mapping = "3001:8084"
        actual_mapping = config.get_port_mapping()
        
        if actual_mapping != expected_mapping:
            raise ValueError(f"Invalid port mapping: {actual_mapping}, expected: {expected_mapping}")
        
        # Verify server type
        if config.get_server_type() != 'python':
            raise ValueError(f"Invalid server type: {config.get_server_type()}, expected: python")
        
        # Verify zero-trust settings
        if not config.verify_zero_trust_config():
            raise ValueError("Zero-trust security not properly configured")
        
        return True
        
    except ImportError:
        raise ImportError("PolyCallConfig module not found. Please ensure proper installation.")
    except Exception as e:
        raise RuntimeError(f"Configuration validation failed: {e}")

def check_installation():
    """Check if PyPolyCall is properly installed and configured"""
    try:
        # Check configuration
        validate_config()
        
        # Check port availability
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', 8084))
            server_running = result == 0
        
        status = {
            'installed': True,
            'configured': True,
            'server_running': server_running,
            'port_mapping': '3001:8084',
            'binding_type': 'python'
        }
        
        return status
        
    except Exception as e:
        return {
            'installed': True,
            'configured': False,
            'server_running': False,
            'error': str(e)
        }
