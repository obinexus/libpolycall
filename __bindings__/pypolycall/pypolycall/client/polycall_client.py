"""
PolyCall client implementation for PyPolyCall.

This module provides the high-level client API for the PyPolyCall library,
integrating protocol, network, and state management components.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any, Callable, TypeVar, Generic

from ..core.types import (
    MessageType, ProtocolFlags, ProtocolState, CoreError, 
    ErrorSource, PolyCallException
)
from ..core.context import CoreContext
from ..core.error import set_error, check_params
from ..protocol.protocol_handler import ProtocolHandler, ProtocolMessage
from ..network.endpoint import NetworkEndpoint, ConnectionState, EndpointType
from .router import Router

# Configure logger
logger = logging.getLogger("pypolycall.client")

# Type for response data
T = TypeVar('T')


class PolyCallClient:
    """High-level client for the PyPolyCall library."""
    
    def __init__(
        self,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the PolyCall client.
        
        Args:
            options: Client options
        """
        # Default options
        self.options = {
            "host": "localhost",
            "port": 8084,  # Default port for bindings
            "reconnect": True,
            "timeout": 5000,  # ms
            "max_retries": 3,
            "protocol_version": 1,
        }
        
        # Update with provided options
        if options:
            self.options.update(options)
        
        # Create core context
        self.core_ctx = CoreContext("polycall_client")
        
        # Create protocol handler
        self.protocol = ProtocolHandler(
            self.core_ctx,
            protocol_version=self.options["protocol_version"]
        )
        
        # Create network endpoint
        self.endpoint = NetworkEndpoint(
            self.core_ctx,
            self.protocol,
            endpoint_type=EndpointType.CLIENT,
            options=self.options
        )
        
        # Create router
        self.router = Router()
        
        # State
        self.connected = False
        self.authenticated = False
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable[..., Any]]] = {
            'connected': [],
            'disconnected': [],
            'authenticated': [],
            'error': [],
            'state:changed': [],
            'command': [],
            'response': []
        }
        
        # Set up event handlers for endpoint and protocol
        self._setup_event_handlers()
    
    def _setup_event_handlers(self) -> None:
        """Set up event handlers for endpoint and protocol."""
        # Endpoint events
        self.endpoint.on('connected', self._on_connected)
        self.endpoint.on('disconnected', self._on_disconnected)
        self.endpoint.on('error', self._on_error)
        
        # Protocol events
        self.protocol.register_handler(MessageType.HANDSHAKE, self._on_handshake)
        self.protocol.register_handler(MessageType.AUTH, self._on_auth)
        self.protocol.register_handler(MessageType.COMMAND, self._on_command)
        self.protocol.register_handler(MessageType.RESPONSE, self._on_response)
        self.protocol.register_handler(MessageType.ERROR, self._on_protocol_error)
    
    def _on_connected(self) -> None:
        """Handle connected event."""
        self.connected = True
        self._notify_event('connected')
        
        # Start protocol handler
        self.protocol.start()
        
        # Begin handshake
        asyncio.create_task(self._initiate_handshake())
    
    def _on_disconnected(self) -> None:
        """Handle disconnected event."""
        self.connected = False
        self.authenticated = False
        self._notify_event('disconnected')
    
    def _on_error(self, error: Exception) -> None:
        """
        Handle error event.
        
        Args:
            error: Error
        """
        self._notify_event('error', error)
    
    def _on_handshake(self, message: ProtocolMessage) -> None:
        """
        Handle handshake message.
        
        Args:
            message: Protocol message
        """
        # Protocol handler already processed handshake
        if self.protocol.handshake_complete:
            logger.info("Handshake completed")
    
    def _on_auth(self, message: ProtocolMessage) -> None:
        """
        Handle auth message.
        
        Args:
            message: Protocol message
        """
        # Protocol handler already processed auth
        if self.protocol.authenticated:
            self.authenticated = True
            self._notify_event('authenticated')
            logger.info("Authentication completed")
    
    def _on_command(self, message: ProtocolMessage) -> None:
        """
        Handle command message.
        
        Args:
            message: Protocol message
        """
        try:
            # Parse command data
            command_data = json.loads(message.payload.decode('utf-8'))
            
            # Notify event handlers
            self._notify_event('command', command_data)
            
            # Process with router if appropriate
            if isinstance(command_data, dict) and 'path' in command_data:
                asyncio.create_task(self._process_command_with_router(command_data))
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
    
    async def _process_command_with_router(self, command_data: Dict[str, Any]) -> None:
        """
        Process a command with the router.
        
        Args:
            command_data: Command data
        """
        try:
            path = command_data.get('path', '/')
            method = command_data.get('method', 'GET')
            data = command_data.get('data', {})
            
            # Process with router
            result = await self.router.handle_request(path, method, data)
            
            # Send response
            await self.send_response(command_data.get('id'), result)
            
        except Exception as e:
            logger.error(f"Error processing command with router: {e}")
            
            # Send error response
            await self.send_error(command_data.get('id'), str(e))
    
    def _on_response(self, message: ProtocolMessage) -> None:
        """
        Handle response message.
        
        Args:
            message: Protocol message
        """
        try:
            # Parse response data
            response_data = json.loads(message.payload.decode('utf-8'))
            
            # Notify event handlers
            self._notify_event('response', response_data)
            
        except Exception as e:
            logger.error(f"Error processing response: {e}")
    
    def _on_protocol_error(self, message: ProtocolMessage) -> None:
        """
        Handle protocol error message.
        
        Args:
            message: Protocol message
        """
        try:
            # Parse error data
            error_data = json.loads(message.payload.decode('utf-8'))
            
            # Create exception
            error = PolyCallException(
                CoreError.PROTOCOL,
                error_data.get('error', 'Unknown protocol error')
            )
            
            # Notify event handlers
            self._notify_event('error', error)
            
        except Exception as e:
            logger.error(f"Error processing protocol error: {e}")
    
    async def _initiate_handshake(self) -> None:
        """Initiate handshake with the server."""
        try:
            await self.protocol.start_handshake()
        except Exception as e:
            logger.error(f"Handshake failed: {e}")
            self._notify_event('error', e)
    
    async def connect(self) -> bool:
        """
        Connect to the server.
        
        Returns:
            True if connection succeeded, False otherwise
        """
        if self.connected:
            return True
        
        try:
            return await self.endpoint.connect()
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._notify_event('error', e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if not self.connected:
            return
        
        try:
            await self.endpoint.disconnect()
        except Exception as e:
            logger.error(f"Disconnection failed: {e}")
            self._notify_event('error', e)
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with the server.
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self.connected:
            raise PolyCallException(
                CoreError.INVALID_STATE,
                "Not connected to server"
            )
        
        if self.authenticated:
            return True
        
        try:
            result = await self.protocol.authenticate(credentials)
            
            if result:
                self.authenticated = True
                self._notify_event('authenticated')
            
            return result
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._notify_event('error', e)
            return False
    
    async def send_request(
        self,
        path: str,
        method: str = 'GET',
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a request to the server.
        
        Args:
            path: Request path
            method: Request method
            data: Request data
        
        Returns:
            Response data
        """
        if not self.connected:
            raise PolyCallException(
                CoreError.INVALID_STATE,
                "Not connected to server"
            )
        
        try:
            # Route request locally
            return await self.router.handle_request(path, method, data or {})
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self._notify_event('error', e)
            raise
    
    async def execute_command(
        self,
        command: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a command on the server.
        
        Args:
            command: Command name
            data: Command data
        
        Returns:
            Command result
        """
        if not self.authenticated:
            raise PolyCallException(
                CoreError.UNAUTHORIZED,
                "Not authenticated"
            )
        
        try:
            # Create command message
            command_data = {
                'command': command,
                'data': data or {},
                'id': str(int(time.time() * 1000)),
                'timestamp': time.time()
            }
            
            # Send command
            payload = json.dumps(command_data).encode('utf-8')
            response = await self.protocol.send_message(
                MessageType.COMMAND,
                payload,
                ProtocolFlags.RELIABLE
            )
            
            # Parse response
            response_data = json.loads(response.payload.decode('utf-8'))
            
            return response_data
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            self._notify_event('error', e)
            raise
    
    async def send_response(
        self,
        request_id: Optional[str],
        data: Any
    ) -> None:
        """
        Send a response to a command.
        
        Args:
            request_id: Request ID
            data: Response data
        """
        if not request_id:
            return
        
        try:
            # Create response message
            response_data = {
                'id': request_id,
                'data': data,
                'timestamp': time.time()
            }
            
            # Send response
            payload = json.dumps(response_data).encode('utf-8')
            await self.protocol.send_message(
                MessageType.RESPONSE,
                payload,
                ProtocolFlags.RELIABLE
            )
            
        except Exception as e:
            logger.error(f"Send response failed: {e}")
    
    async def send_error(
        self,
        request_id: Optional[str],
        error_message: str
    ) -> None:
        """
        Send an error response to a command.
        
        Args:
            request_id: Request ID
            error_message: Error message
        """
        if not request_id:
            return
        
        try:
            # Create error message
            error_data = {
                'id': request_id,
                'error': error_message,
                'timestamp': time.time()
            }
            
            # Send error
            payload = json.dumps(error_data).encode('utf-8')
            await self.protocol.send_message(
                MessageType.ERROR,
                payload,
                ProtocolFlags.RELIABLE
            )
            
        except Exception as e:
            logger.error(f"Send error failed: {e}")
    
    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """
        Register an event handler.
        
        Args:
            event: Event name
            handler: Event handler function
        """
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """
        Unregister an event handler.
        
        Args:
            event: Event name
            handler: Event handler function
        """
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass
    
    def _notify_event(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Notify event handlers.
        
        Args:
            event: Event name
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
    
    def is_connected(self) -> bool:
        """
        Check if the client is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.authenticated
    
    async def get_state(self, state_name: str) -> Dict[str, Any]:
        """
        Get a specific state.
        
        Args:
            state_name: State name
        
        Returns:
            State data
        """
        return await self.send_request(f'/states/{state_name}')
    
    async def get_all_states(self) -> Dict[str, Any]:
        """
        Get all states.
        
        Returns:
            States data
        """
        return await self.send_request('/states')
    
    async def lock_state(self, state_name: str) -> Dict[str, Any]:
        """
        Lock a specific state.
        
        Args:
            state_name: State name
        
        Returns:
            Response data
        """
        return await self.send_request(f'/states/{state_name}/lock', 'POST')
    
    async def unlock_state(self, state_name: str) -> Dict[str, Any]:
        """
        Unlock a specific state.
        
        Args:
            state_name: State name
        
        Returns:
            Response data
        """
        return await self.send_request(f'/states/{state_name}/unlock', 'POST')
    
    async def transition_to(self, state_name: str) -> Dict[str, Any]:
        """
        Transition to a state.
        
        Args:
            state_name: Target state name
        
        Returns:
            Response data
        """
        result = await self.send_request(f'/transition/{state_name}', 'POST')
        
        # Notify state change
        self._notify_event('state:changed', {
            'from': result.get('from'),
            'to': result.get('to')
        })
        
        return result