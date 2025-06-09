"""
Error handling module for PyPolyCall.

This module implements error tracking, error callbacks, and
utilities for error propagation throughout the PyPolyCall system.
"""

from asyncio import Protocol
import traceback
import inspect
import logging
import time
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, field

from .types import CoreError, ErrorRecord, ErrorSeverity, ErrorSource, PolyCallException

# Configure logger
logger = logging.getLogger("pypolycall.error")


class ErrorCallback(Protocol):
    """Protocol for error callback functions."""
    def __call__(self, record: ErrorRecord, context: Any) -> None:
        ...


class ErrorManager:
    """Centralized error management for PyPolyCall."""
    
    def __init__(self):
        """Initialize the error manager."""
        self._last_error: Optional[ErrorRecord] = None
        self._callbacks: List[Tuple[ErrorCallback, Any]] = []
        self._error_history: List[ErrorRecord] = []
        self._max_history_size = 50  # Keep last 50 errors by default
    
    def set_error(
        self,
        source: ErrorSource,
        code: CoreError,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        file: Optional[str] = None,
        line: Optional[int] = None,
        context: Any = None
    ) -> CoreError:
        """
        Set a new error and trigger callbacks.
        
        Args:
            source: Error source module
            code: Error code
            message: Error message
            severity: Error severity level
            file: Source file (auto-detected if None)
            line: Source line (auto-detected if None)
            context: Associated context
        
        Returns:
            The error code for convenient error propagation
        """
        # Auto-detect file and line if not provided
        if file is None or line is None:
            frame = inspect.currentframe()
            if frame is not None:
                frame = frame.f_back  # Get caller's frame
                if frame is not None:
                    if file is None:
                        file = frame.f_code.co_filename
                    if line is None:
                        line = frame.f_lineno
        
        # Create error record
        record = ErrorRecord(
            source=source,
            code=code,
            severity=severity,
            message=message,
            file=file,
            line=line,
            timestamp=time.time()
        )
        
        # Store as last error
        self._last_error = record
        
        # Add to history, maintaining max size
        self._error_history.append(record)
        if len(self._error_history) > self._max_history_size:
            self._error_history.pop(0)
        
        # Log the error
        log_message = f"[{source.name}] {code.name}: {message}"
        if severity == ErrorSeverity.FATAL:
            logger.critical(log_message)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Notify callbacks
        for callback, callback_context in self._callbacks:
            try:
                callback(record, callback_context or context)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
                logger.debug(traceback.format_exc())
        
        return code
    
    def register_callback(self, callback: ErrorCallback, user_data: Any = None) -> None:
        """
        Register an error callback function.
        
        Args:
            callback: The callback function to register
            user_data: User data to pass to the callback
        """
        self._callbacks.append((callback, user_data))
    
    def unregister_callback(self, callback: ErrorCallback) -> bool:
        """
        Unregister an error callback function.
        
        Args:
            callback: The callback function to unregister
        
        Returns:
            True if the callback was found and removed, False otherwise
        """
        for i, (cb, _) in enumerate(self._callbacks):
            if cb == callback:
                self._callbacks.pop(i)
                return True
        return False
    
    def get_last_error(self) -> Optional[ErrorRecord]:
        """
        Get the last error record.
        
        Returns:
            The last error record, or None if no error has occurred
        """
        return self._last_error
    
    def clear_last_error(self) -> None:
        """Clear the last error."""
        self._last_error = None
    
    def has_error(self) -> bool:
        """
        Check if an error has occurred.
        
        Returns:
            True if an error has occurred, False otherwise
        """
        return self._last_error is not None
    
    def get_error_history(self) -> List[ErrorRecord]:
        """
        Get the error history.
        
        Returns:
            List of error records in chronological order
        """
        return self._error_history.copy()
    
    def clear_error_history(self) -> None:
        """Clear the error history."""
        self._error_history.clear()
    
    def set_max_history_size(self, size: int) -> None:
        """
        Set the maximum error history size.
        
        Args:
            size: Maximum number of error records to keep
        """
        if size < 0:
            raise ValueError("History size cannot be negative")
        
        self._max_history_size = size
        
        # Trim history if needed
        while len(self._error_history) > self._max_history_size:
            self._error_history.pop(0)


# Global error manager instance
_error_manager = ErrorManager()


def get_error_manager() -> ErrorManager:
    """
    Get the global error manager instance.
    
    Returns:
        The global error manager
    """
    return _error_manager


def set_error(
    source: ErrorSource,
    code: CoreError,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    file: Optional[str] = None,
    line: Optional[int] = None,
    context: Any = None
) -> CoreError:
    """
    Set a new error using the global error manager.
    
    Args:
        source: Error source module
        code: Error code
        message: Error message
        severity: Error severity level
        file: Source file (auto-detected if None)
        line: Source line (auto-detected if None)
        context: Associated context
    
    Returns:
        The error code for convenient error propagation
    """
    # If file/line not specified, detect from caller's frame
    if file is None or line is None:
        frame = inspect.currentframe()
        if frame:
            frame = frame.f_back  # Get caller's frame
            if frame:
                if file is None:
                    file = frame.f_code.co_filename
                if line is None:
                    line = frame.f_lineno
    
    return _error_manager.set_error(
        source=source,
        code=code,
        message=message,
        severity=severity,
        file=file,
        line=line,
        context=context
    )


def throw_if_error(source: ErrorSource, condition: bool, code: CoreError, message: str) -> None:
    """
    Throw a PolyCallException if the condition is True.
    
    Args:
        source: Error source module
        condition: Condition to check
        code: Error code to use if condition is True
        message: Error message to use if condition is True
    
    Raises:
        PolyCallException: If the condition is True
    """
    if condition:
        set_error(source, code, message)
        raise PolyCallException(code, message)


def check_params(*args: Any) -> None:
    """
    Check if any parameters are None and raise an appropriate exception.
    
    Args:
        *args: Parameters to check
    
    Raises:
        PolyCallException: If any parameter is None
    """
    if None in args:
        set_error(
            ErrorSource.CORE, 
            CoreError.INVALID_PARAMETERS,
            "One or more parameters are None"
        )
        raise PolyCallException(
            CoreError.INVALID_PARAMETERS, 
            "One or more parameters are None"
        )