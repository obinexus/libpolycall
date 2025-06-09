"""
Context management module for PyPolyCall.

This module provides unified state tracking and resource management
for the Program-First design approach. The context system serves as a central
repository for program state that can be referenced by any module.
"""

import threading
import time
import uuid
import weakref
from typing import Dict, Optional, List, Callable, Any, TypeVar, Generic, Set, Union, Type

from .types import ContextType, ContextFlags, CoreError
from .error import set_error, ErrorSource, throw_if_error, check_params

# Type definitions
T = TypeVar('T')
ContextListener = Callable[['ContextRef', Any], None]


class ContextRef(Generic[T]):
    """Reference to a context with metadata."""
    
    def __init__(
        self,
        context_type: ContextType,
        name: str,
        flags: ContextFlags = ContextFlags.NONE,
        data: Optional[T] = None,
        data_size: int = 0
    ):
        """
        Initialize a context reference.
        
        Args:
            context_type: Context type
            name: Context name
            flags: Context flags
            data: Context data
            data_size: Context data size
        """
        self.type = context_type
        self.name = name
        self.flags = flags
        self.data = data
        self.data_size = data_size
        self.lock = threading.RLock()
        self.listeners: List[tuple[ContextListener, Any]] = []
        self.shared_with: Set[str] = set()
        self.creation_time = time.time()
        self.last_modified_time = self.creation_time
    
    def __enter__(self) -> 'ContextRef[T]':
        """Enter context for use in 'with' statements."""
        self.lock.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context for use in 'with' statements."""
        self.lock.release()
    
    def notify_listeners(self) -> None:
        """Notify all registered listeners of a change."""
        with self.lock:
            for listener, user_data in self.listeners:
                try:
                    listener(self, user_data)
                except Exception as e:
                    set_error(
                        ErrorSource.CONTEXT,
                        CoreError.INTERNAL,
                        f"Error in context listener: {e}"
                    )


class ContextRegistry:
    """Registry of all context references."""
    
    def __init__(self):
        """Initialize the context registry."""
        self.contexts: Dict[str, ContextRef] = {}
        self.registry_lock = threading.RLock()
    
    def register(self, ctx_ref: ContextRef) -> None:
        """
        Register a context reference.
        
        Args:
            ctx_ref: Context reference to register
        """
        with self.registry_lock:
            self.contexts[ctx_ref.name] = ctx_ref
    
    def unregister(self, ctx_ref: ContextRef) -> None:
        """
        Unregister a context reference.
        
        Args:
            ctx_ref: Context reference to unregister
        """
        with self.registry_lock:
            if ctx_ref.name in self.contexts:
                del self.contexts[ctx_ref.name]
    
    def find_by_name(self, name: str) -> Optional[ContextRef]:
        """
        Find a context reference by name.
        
        Args:
            name: Context name
        
        Returns:
            Context reference if found, None otherwise
        """
        with self.registry_lock:
            return self.contexts.get(name)
    
    def find_by_type(self, context_type: ContextType) -> List[ContextRef]:
        """
        Find all context references of a specific type.
        
        Args:
            context_type: Context type
        
        Returns:
            List of context references of the specified type
        """
        with self.registry_lock:
            return [ctx for ctx in self.contexts.values() if ctx.type == context_type]
    
    def get_all(self) -> List[ContextRef]:
        """
        Get all registered contexts.
        
        Returns:
            List of all context references
        """
        with self.registry_lock:
            return list(self.contexts.values())


# Global context registry
_registry = ContextRegistry()


def get_registry() -> ContextRegistry:
    """
    Get the global context registry.
    
    Returns:
        The global context registry
    """
    return _registry


class CoreContext:
    """Core context for PyPolyCall."""
    
    def __init__(self, name: str = "core_context"):
        """
        Initialize the core context.
        
        Args:
            name: Context name
        """
        self.name = name
        self.user_data: Any = None
        self.refs: Dict[str, weakref.ReferenceType[ContextRef]] = {}
        self.registry = _registry
        
        # Create a reference to this context
        self.ref = ContextRef(
            context_type=ContextType.CORE,
            name=name,
            flags=ContextFlags.INITIALIZED,
            data=self
        )
        
        # Register this context
        self.registry.register(self.ref)
    
    def __del__(self):
        """Clean up resources when the context is destroyed."""
        self.cleanup()
    
    def set_user_data(self, user_data: Any) -> None:
        """
        Set user data.
        
        Args:
            user_data: User data to set
        """
        self.user_data = user_data
    
    def get_user_data(self) -> Any:
        """
        Get user data.
        
        Returns:
            User data
        """
        return self.user_data
    
    def create_context(
        self,
        context_type: ContextType,
        name: str,
        data: Optional[T] = None,
        flags: ContextFlags = ContextFlags.NONE,
        init_fn: Optional[Callable[[Any, T, Any], CoreError]] = None,
        init_data: Any = None
    ) -> Optional[ContextRef[T]]:
        """
        Create a new context.
        
        Args:
            context_type: Context type
            name: Context name
            data: Context data
            flags: Context flags
            init_fn: Initialization function
            init_data: Initialization data
        
        Returns:
            Context reference, or None on error
        """
        check_params(name)
        
        # Check if a context with the same name already exists
        if self.registry.find_by_name(name) is not None:
            set_error(
                ErrorSource.CONTEXT,
                CoreError.ALREADY_INITIALIZED,
                f"Context '{name}' already exists"
            )
            return None
        
        # Create context reference
        ctx_ref = ContextRef(
            context_type=context_type,
            name=name,
            flags=flags,
            data=data
        )
        
        # Initialize with init function if provided
        if init_fn and data:
            result = init_fn(self, data, init_data)
            if result != CoreError.SUCCESS:
                set_error(
                    ErrorSource.CONTEXT,
                    CoreError.INITIALIZATION_FAILED,
                    f"Failed to initialize context '{name}': {result}"
                )
                return None
        
        # Mark as initialized
        ctx_ref.flags |= ContextFlags.INITIALIZED
        
        # Register the context
        self.registry.register(ctx_ref)
        
        # Store weak reference
        self.refs[name] = weakref.ref(ctx_ref)
        
        return ctx_ref
    
    def get_context(self, name: str) -> Optional[ContextRef]:
        """
        Get a context by name.
        
        Args:
            name: Context name
        
        Returns:
            Context reference if found, None otherwise
        """
        return self.registry.find_by_name(name)
    
    def get_context_by_type(self, context_type: ContextType) -> Optional[ContextRef]:
        """
        Get the first context of a specific type.
        
        Args:
            context_type: Context type
        
        Returns:
            Context reference if found, None otherwise
        """
        contexts = self.registry.find_by_type(context_type)
        return contexts[0] if contexts else None
    
    def cleanup(self) -> None:
        """Clean up all resources associated with this context."""
        # Clean up all contexts created by this context
        for name, weak_ref in list(self.refs.items()):
            ctx_ref = weak_ref()
            if ctx_ref:
                self.cleanup_context(ctx_ref)
        
        # Unregister this context
        self.registry.unregister(self.ref)
    
    def cleanup_context(self, ctx_ref: ContextRef) -> None:
        """
        Clean up a specific context.
        
        Args:
            ctx_ref: Context reference to clean up
        """
        # Remove from registry
        self.registry.unregister(ctx_ref)
        
        # Remove from refs
        name = ctx_ref.name
        if name in self.refs:
            del self.refs[name]
    
    def lock_context(self, ctx_ref: ContextRef) -> CoreError:
        """
        Lock a context.
        
        Args:
            ctx_ref: Context reference to lock
        
        Returns:
            Error code
        """
        with ctx_ref.lock:
            # Check if already locked
            if ctx_ref.flags & ContextFlags.LOCKED:
                return CoreError.INVALID_STATE
            
            # Lock context
            ctx_ref.flags |= ContextFlags.LOCKED
            
            # Notify listeners
            ctx_ref.notify_listeners()
            
            return CoreError.SUCCESS
    
    def unlock_context(self, ctx_ref: ContextRef) -> CoreError:
        """
        Unlock a context.
        
        Args:
            ctx_ref: Context reference to unlock
        
        Returns:
            Error code
        """
        with ctx_ref.lock:
            # Check if not locked
            if not (ctx_ref.flags & ContextFlags.LOCKED):
                return CoreError.INVALID_STATE
            
            # Unlock context
            ctx_ref.flags &= ~ContextFlags.LOCKED
            
            # Notify listeners
            ctx_ref.notify_listeners()
            
            return CoreError.SUCCESS
    
    def share_context(self, ctx_ref: ContextRef, component: str) -> CoreError:
        """
        Share a context with another component.
        
        Args:
            ctx_ref: Context reference to share
            component: Component to share with
        
        Returns:
            Error code
        """
        check_params(component)
        
        with ctx_ref.lock:
            # Check if isolated
            if ctx_ref.flags & ContextFlags.ISOLATED:
                return CoreError.UNSUPPORTED_OPERATION
            
            # Share context
            ctx_ref.shared_with.add(component)
            ctx_ref.flags |= ContextFlags.SHARED
            
            # Notify listeners
            ctx_ref.notify_listeners()
            
            return CoreError.SUCCESS
    
    def unshare_context(self, ctx_ref: ContextRef, component: str) -> CoreError:
        """
        Unshare a context with a component.
        
        Args:
            ctx_ref: Context reference to unshare
            component: Component to unshare with
        
        Returns:
            Error code
        """
        check_params(component)
        
        with ctx_ref.lock:
            # Remove from shared components
            if component in ctx_ref.shared_with:
                ctx_ref.shared_with.remove(component)
            
            # If no more shared components, clear shared flag
            if not ctx_ref.shared_with:
                ctx_ref.flags &= ~ContextFlags.SHARED
            
            # Notify listeners
            ctx_ref.notify_listeners()
            
            return CoreError.SUCCESS
    
    def isolate_context(self, ctx_ref: ContextRef) -> CoreError:
        """
        Isolate a context.
        
        Args:
            ctx_ref: Context reference to isolate
        
        Returns:
            Error code
        """
        with ctx_ref.lock:
            # Check if shared
            if ctx_ref.flags & ContextFlags.SHARED:
                return CoreError.INVALID_STATE
            
            # Isolate context
            ctx_ref.flags |= ContextFlags.ISOLATED
            
            # Notify listeners
            ctx_ref.notify_listeners()
            
            return CoreError.SUCCESS
    
    def register_listener(
        self,
        ctx_ref: ContextRef,
        listener: ContextListener,
        user_data: Any = None
    ) -> CoreError:
        """
        Register a context listener.
        
        Args:
            ctx_ref: Context reference
            listener: Listener function
            user_data: User data to pass to listener
        
        Returns:
            Error code
        """
        check_params(ctx_ref, listener)
        
        with ctx_ref.lock:
            # Add listener
            ctx_ref.listeners.append((listener, user_data))
            
            return CoreError.SUCCESS
    
    def unregister_listener(
        self,
        ctx_ref: ContextRef,
        listener: ContextListener
    ) -> CoreError:
        """
        Unregister a context listener.
        
        Args:
            ctx_ref: Context reference
            listener: Listener function to unregister
        
        Returns:
            Error code
        """
        check_params(ctx_ref, listener)
        
        with ctx_ref.lock:
            # Find and remove listener
            for i, (l, _) in enumerate(ctx_ref.listeners):
                if l == listener:
                    ctx_ref.listeners.pop(i)
                    return CoreError.SUCCESS
            
            return CoreError.NOT_FOUND