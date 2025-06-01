# state.py - PyPolyCall State Implementation
import time
import re
import json
from typing import Dict, Any, Callable, Set, Optional
from dataclasses import dataclass, field


class State:
    """PyPolyCall State - Python equivalent of State.js"""
    
    def __init__(self, name: str, options: Dict[str, Any] = None):
        if options is None:
            options = {}
            
        # Ensure name is a string and not empty
        if not name or not isinstance(name, str):
            raise ValueError('State name must be a non-empty string')
        
        self.name = name
        self.is_locked = False
        self.handlers: Dict[str, Callable] = {}
        self.metadata: Dict[str, Any] = {}
        self.transitions: Set[str] = set()
        
        # Safely create endpoint from name
        default_endpoint = f"/{name.strip().lower()}"
        default_endpoint = re.sub(r'\s+', '-', default_endpoint)
        self.endpoint = options.get('endpoint', default_endpoint)
        
        self.timeout = options.get('timeout', 5000)
        self.retry_count = options.get('retry_count', 3)
        
        # Initialize state metadata
        self.metadata['created_at'] = int(time.time() * 1000)
        self.metadata['version'] = 1
        self.metadata['last_modified'] = int(time.time() * 1000)
    
    # Handler management
    def add_handler(self, event: str, handler: Callable):
        """Add an event handler"""
        if not callable(handler):
            raise ValueError('Handler must be a function')
        self.handlers[event] = handler
        return self
    
    def remove_handler(self, event: str):
        """Remove an event handler"""
        if event in self.handlers:
            del self.handlers[event]
        return self
    
    async def execute_handler(self, event: str, *args):
        """Execute a handler for an event"""
        if self.is_locked:
            raise RuntimeError(f"State {self.name} is locked")
        
        handler = self.handlers.get(event)
        if not handler:
            raise RuntimeError(f"No handler found for event {event} in state {self.name}")
        
        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                return await handler(*args)
            else:
                return handler(*args)
        except Exception as error:
            # Emit error event (would need event system)
            raise error
    
    # State locking
    def lock(self):
        """Lock the state"""
        if self.is_locked:
            raise RuntimeError(f"State {self.name} is already locked")
        self.is_locked = True
        self.metadata['locked_at'] = int(time.time() * 1000)
        # Emit locked event (would need event system)
        return self
    
    def unlock(self):
        """Unlock the state"""
        if not self.is_locked:
            raise RuntimeError(f"State {self.name} is not locked")
        self.is_locked = False
        if 'locked_at' in self.metadata:
            del self.metadata['locked_at']
        # Emit unlocked event (would need event system)
        return self
    
    # Transition management
    def add_transition(self, to_state: str):
        """Add a valid transition"""
        self.transitions.add(to_state)
        return self
    
    def can_transition_to(self, target_state: str) -> bool:
        """Check if transition to target state is allowed"""
        return target_state in self.transitions
    
    # Endpoint management
    def get_endpoint(self) -> str:
        """Get the endpoint URL"""
        return self.endpoint
    
    def set_endpoint(self, endpoint: str):
        """Set the endpoint URL"""
        if not isinstance(endpoint, str) or not endpoint.startswith('/'):
            raise ValueError('Endpoint must be a string starting with /')
        self.endpoint = endpoint
        return self
    
    # State verification
    def verify(self) -> Dict[str, Any]:
        """Verify state and return status"""
        return {
            'name': self.name,
            'is_locked': self.is_locked,
            'handler_count': len(self.handlers),
            'transition_count': len(self.transitions),
            'metadata': self.metadata.copy(),
            'endpoint': self.endpoint
        }
    
    # Metadata management
    def set_metadata(self, key: str, value: Any):
        """Set metadata value"""
        self.metadata[key] = value
        self.metadata['last_modified'] = int(time.time() * 1000)
        self.metadata['version'] = self.metadata.get('version', 0) + 1
        return self
    
    def get_metadata(self, key: str) -> Any:
        """Get metadata value"""
        return self.metadata.get(key)
    
    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            'name': self.name,
            'is_locked': self.is_locked,
            'endpoint': self.endpoint,
            'metadata': self.metadata.copy(),
            'transitions': list(self.transitions)
        }
    
    def to_json(self) -> str:
        """Convert state to JSON string"""
        return json.dumps(self.to_dict())
    
    # Create state snapshot
    def create_snapshot(self) -> Dict[str, Any]:
        """Create a state snapshot"""
        return {
            'timestamp': int(time.time() * 1000),
            'state': self.to_dict(),
            'checksum': self.calculate_state_checksum()
        }
    
    # Restore from snapshot
    def restore_from_snapshot(self, snapshot: Dict[str, Any]):
        """Restore state from snapshot"""
        if not snapshot or 'state' not in snapshot or 'checksum' not in snapshot:
            raise ValueError('Invalid snapshot format')
        
        if snapshot['checksum'] != self.calculate_state_checksum(snapshot['state']):
            raise ValueError('Snapshot checksum verification failed')
        
        state_data = snapshot['state']
        self.name = state_data['name']
        self.is_locked = state_data['is_locked']
        self.endpoint = state_data['endpoint']
        self.metadata = state_data['metadata'].copy()
        self.transitions = set(state_data['transitions'])
        
        # Emit restored event (would need event system)
        return self
    
    # Calculate state checksum
    def calculate_state_checksum(self, state_data: Optional[Dict[str, Any]] = None) -> int:
        """Calculate checksum for state data"""
        if state_data is None:
            state_data = self.to_dict()
        
        checksum = 0
        state_string = json.dumps(state_data, sort_keys=True)
        
        for char in state_string:
            checksum = ((checksum << 5) - checksum) + ord(char)
            checksum = checksum & 0xFFFFFFFF  # Convert to 32-bit integer
        
        return checksum & 0x7FFFFFFF  # Convert to unsigned
    
    def __str__(self) -> str:
        return f"State(name={self.name}, locked={self.is_locked}, endpoint={self.endpoint})"
    
    def __repr__(self) -> str:
        return self.__str__()
