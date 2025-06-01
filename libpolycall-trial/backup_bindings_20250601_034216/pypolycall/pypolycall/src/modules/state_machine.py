# state_machine.py - PyPolyCall State Machine Implementation
from typing import Dict, Any, List, Optional
from .state import State

class StateMachine:
    """PyPolyCall State Machine - Python equivalent of StateMachine.js"""
    
    def __init__(self, options: Dict[str, Any] = None):
        if options is None:
            options = {}
            
        self.states: Dict[str, State] = {}
        self.transitions: Dict[str, Dict[str, Any]] = {}
        self.current_state: Optional[State] = None
        self.history: List[Dict[str, Any]] = []
        self.max_history_length = options.get('max_history_length', 100)
        
        self.options = {
            'allow_self_transitions': False,
            'validate_state_change': True,
            'record_history': True,
            **options
        }
    
    def add_state(self, name: str, options: Dict[str, Any] = None) -> State:
        """Add a new state"""
        if name in self.states:
            raise ValueError(f"State {name} already exists")
        
        if options is None:
            options = {}
            
        state = State(name, options)
        self.states[name] = state
        
        # Set initial state if none exists
        if self.current_state is None and not options.get('defer', False):
            self.current_state = state
        
        return state
    
    def get_state(self, name: str) -> State:
        """Get state by name"""
        if name not in self.states:
            raise ValueError(f"State {name} does not exist")
        return self.states[name]
    
    def get_current_state(self) -> Optional[State]:
        """Get current state"""
        return self.current_state
    
    def add_transition(self, from_state: str, to_state: str, options: Dict[str, Any] = None):
        """Add state transition"""
        if options is None:
            options = {}
            
        if from_state not in self.states:
            raise ValueError(f"Source state {from_state} does not exist")
        if to_state not in self.states:
            raise ValueError(f"Target state {to_state} does not exist")
        
        transition_key = f"{from_state}->{to_state}"
        transition = {
            'from': from_state,
            'to': to_state,
            'guard': options.get('guard', lambda: True),
            'before': options.get('before', lambda: None),
            'after': options.get('after', lambda: None),
            **options
        }
        
        self.transitions[transition_key] = transition
        self.states[from_state].add_transition(to_state)
        
        return self
    
    async def execute_transition(self, to_state: str) -> bool:
        """Execute state transition"""
        if not self.current_state:
            raise RuntimeError('No current state')
        
        target_state = self.get_state(to_state)
        transition_key = f"{self.current_state.name}->{target_state.name}"
        
        if transition_key not in self.transitions:
            raise ValueError(f"No transition defined from {self.current_state.name} to {target_state.name}")
        
        transition = self.transitions[transition_key]
        
        # Check guard condition
        if not transition['guard']():
            raise RuntimeError('Transition guard condition failed')
        
        try:
            # Execute transition
            from_state = self.current_state
            
            # Before transition
            transition['before']()
            
            # Perform transition
            self.current_state = target_state
            
            # After transition
            transition['after']()
            
            # Record in history
            if self.options['record_history']:
                self.record_transition(from_state, target_state)
            
            return True
            
        except Exception as error:
            raise error
    
    def record_transition(self, from_state: State, to_state: State):
        """Record transition in history"""
        import time
        
        record = {
            'timestamp': int(time.time() * 1000),
            'from': from_state.name,
            'to': to_state.name
        }
        
        self.history.append(record)
        if len(self.history) > self.max_history_length:
            self.history.pop(0)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get transition history"""
        return self.history.copy()
    
    def get_state_names(self) -> List[str]:
        """Get all state names"""
        return list(self.states.keys())
    
    def __str__(self) -> str:
        current = self.current_state.name if self.current_state else 'none'
        return f"StateMachine(current: {current}, states: {len(self.states)})"
