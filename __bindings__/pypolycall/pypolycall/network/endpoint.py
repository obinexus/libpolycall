"""
Network endpoint implementation for PyPolyCall.

This module provides network communication capabilities, handling
connections, retries, and packet management for the PyPolyCall library.
"""

import asyncio
import time
import socket
import ssl
import logging
import json
from typing import Dict, Optional, List, Callable, Any, Union, Tuple, Set, cast
from enum import IntEnum

from ..core.types import PacketFlags, CoreError, ErrorSource
from ..core.error import set_error, check_params, throw_if_error
from ..core.context import CoreContext
from ..protocol.protocol_handler import ProtocolHandler

# Configure logger
logger = logging.getLogger("pypolycall.network")


class EndpointType(IntEnum):
    """Network endpoint types."""
    CLIENT = 0
    SERVER = 1
    PEER = 2


class ConnectionState(IntEnum):
    """Network connection states."""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3
    RECONNECTING = 4
    ERROR = 5


class NetworkEndpoint:
    """Network endpoint for PyPolyCall."""
    
    def __init__(
        self,
        core_ctx: CoreContext,
        protocol_handler: ProtocolHandler,
        endpoint_type: EndpointType = EndpointType.CLIENT,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the network endpoint.
        
        Args:
            core_ctx: Core context
            protocol_handler: Protocol handler
            endpoint_type: Endpoint type
            options: Endpoint options
        """
        self.core_ctx = core_ctx
        self.protocol = protocol_handler
        self.endpoint_type = endpoint_type
        
        # Default options
        self.options = {
            "host": "localhost",
            "port": 8084,  # Default port for bindings
            "timeout": 5000,  # ms
            "keep_alive": True,
            "reconnect": True,
            "max_retries": 3,
            "retry_delay": 1000,  # ms
            "tls_enabled": False,
            "tls_verify": True,
            "tls_cert_file": None,
            "tls_key_file": None,
            "tls_ca_file": None,
            "backlog": 5,  # For server
        }
        
        # Update with provided options
        if options:
            self.options.update(options)
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.retry_count = 0
        self.last_error: Optional[Exception] = None
        
        # Socket
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        
        # For server
        self.server: Optional[asyncio.Server] = None
        self.clients: Dict[Tuple[str, int], Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        
        # Message buffer
        self.pending_data: List[bytes] = []
        
        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Event callbacks
        self._event_handlers: Dict[str, List[Callable[..., Any]]] = {
            'connected': [],
            'disconnected': [],
            'reconnecting': [],
            'error': [],
            'data': [],
            'client_connected': [],
            'client_disconnected': []
        }
    
    async def connect(self) -> bool:
        """
        Connect to the remote endpoint.
        
        Returns:
            True if connection succeeded, False otherwise
        """
        if self.endpoint_type == EndpointType.SERVER:
            return await self.listen()
        
        if self.state in {ConnectionState.CONNECTED, ConnectionState.CONNECTING}:
            return True
        
        self.state = ConnectionState.CONNECTING
        self.retry_count = 0
        
        return await self._connect_internal()
    
    async def _connect_internal(self) -> bool:
        """
        Internal connection method with retry logic.
        
        Returns:
            True if connection succeeded, False otherwise
        """
        while self.retry_count <= self.options["max_retries"]:
            try:
                # Create connection
                if self.options["tls_enabled"]:
                    ssl_context = self._create_ssl_context()
                    self.reader, self.writer = await asyncio.open_connection(
                        self.options["host"],
                        self.options["port"],
                        ssl=ssl_context
                    )
                else:
                    self.reader, self.writer = await asyncio.open_connection(
                        self.options["host"],
                        self.options["port"]
                    )
                
                # Update state
                self.state = ConnectionState.CONNECTED
                self.retry_count = 0
                
                # Start receive task
                if not self._running:
                    self._running = True
                    self._receive_task = asyncio.create_task(self._receive_loop())
                
                # Process any pending data
                for data in self.pending_data:
                    await self.send(data)
                self.pending_data.clear()
                
                # Notify event handlers
                self._notify_event('connected')
                
                return True
                
            except Exception as e:
                self.last_error = e
                logger.error(f"Connection failed: {e}")
                
                # Increase retry count
                self.retry_count += 1
                
                if self.retry_count <= self.options["max_retries"] and self.options["reconnect"]:
                    # Update state
                    self.state = ConnectionState.RECONNECTING
                    
                    # Notify event handlers
                    self._notify_event('reconnecting', self.retry_count)
                    
                    # Wait before retry
                    await asyncio.sleep(self.options["retry_delay"] / 1000)
                else:
                    # Update state
                    self.state = ConnectionState.ERROR
                    
                    # Notify event handlers
                    self._notify_event('error', e)
                    
                    return False
        
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from the remote endpoint."""
        if self.endpoint_type == EndpointType.SERVER:
            await self.stop()
            return
        
        if self.state == ConnectionState.DISCONNECTED:
            return
        
        self.state = ConnectionState.DISCONNECTING
        
        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close writer
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        
        # Reset connection
        self.reader = None
        self.writer = None
        self._running = False
        
        # Update state
        self.state = ConnectionState.DISCONNECTED
        
        # Notify event handlers
        self._notify_event('disconnected')
    
    async def send(self, data: bytes) -> bool:
        """
        Send data to the remote endpoint.
        
        Args:
            data: Data to send
        
        Returns:
            True if send succeeded, False otherwise
        """
        if self.endpoint_type == EndpointType.SERVER:
            # Broadcast to all clients
            for reader, writer in self.clients.values():
                try:
                    writer.write(data)
                    await writer.drain()
                except Exception as e:
                    logger.error(f"Error sending data to client: {e}")
            return True
        
        if self.state != ConnectionState.CONNECTED:
            if self.options["reconnect"] and self.state != ConnectionState.CONNECTING:
                # Store data for later
                self.pending_data.append(data)
                
                # Try to reconnect
                asyncio.create_task(self.connect())
            
            return False
        
        try:
            if self.writer:
                self.writer.write(data)
                await self.writer.drain()
                return True
            
            return False
            
        except Exception as e:
            self.last_error = e
            logger.error(f"Send failed: {e}")
            
            # Connection might be lost, try to reconnect
            if self.options["reconnect"]:
                self.state = ConnectionState.RECONNECTING
                self.pending_data.append(data)
                asyncio.create_task(self._connect_internal())
            else:
                self.state = ConnectionState.ERROR
                
                # Notify event handlers
                self._notify_event('error', e)
            
            return False
    
    async def listen(self) -> bool:
        """
        Start listening for incoming connections (server mode).
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.endpoint_type != EndpointType.SERVER:
            self.endpoint_type = EndpointType.SERVER
        
        if self.server:
            return True
        
        try:
            # Create server
            if self.options["tls_enabled"]:
                ssl_context = self._create_ssl_context()
                self.server = await asyncio.start_server(
                    self._handle_client,
                    self.options["host"],
                    self.options["port"],
                    ssl=ssl_context,
                    backlog=self.options["backlog"]
                )
            else:
                self.server = await asyncio.start_server(
                    self._handle_client,
                    self.options["host"],
                    self.options["port"],
                    backlog=self.options["backlog"]
                )
            
            # Start serving
            asyncio.create_task(self.server.serve_forever())
            
            logger.info(f"Server listening on {self.options['host']}:{self.options['port']}")
            return True
            
        except Exception as e:
            self.last_error = e
            logger.error(f"Failed to start server: {e}")
            
            # Notify event handlers
            self._notify_event('error', e)
            
            return False
    
    async def stop(self) -> None:
        """Stop the server."""
        if not self.server:
            return
        
        # Close server
        self.server.close()
        await self.server.wait_closed()
        self.server = None
        
        # Close all client connections
        for addr, (reader, writer) in list(self.clients.items()):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.error(f"Error closing client connection: {e}")
        
        self.clients.clear()
        
        logger.info("Server stopped")
    
    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle a client connection.
        
        Args:
            reader: Stream reader
            writer: Stream writer
        """
        # Get client address
        addr = writer.get_extra_info('peername')
        logger.info(f"Client connected: {addr}")
        
        # Store client
        self.clients[addr] = (reader, writer)
        
        # Notify event handlers
        self._notify_event('client_connected', addr)
        
        try:
            while True:
                # Read header (16 bytes minimum)
                header_data = await reader.readexactly(16)
                if not header_data:
                    break
                
                # Parse header to get payload length
                payload_length = int.from_bytes(header_data[8:12], byteorder='big')
                
                # Read payload
                payload = await reader.readexactly(payload_length)
                
                # Process message
                message_data = header_data + payload
                
                # Notify event handlers
                self._notify_event('data', message_data)
                
                # Process using protocol handler
                self.protocol.process_received_data(message_data)
                
        except asyncio.IncompleteReadError:
            # Client disconnected
            pass
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        
        # Remove client
        if addr in self.clients:
            del self.clients[addr]
        
        # Notify event handlers
        self._notify_event('client_disconnected', addr)
        
        logger.info(f"Client disconnected: {addr}")
    
    async def _receive_loop(self) -> None:
        """Receive loop for client mode."""
        if not self.reader:
            return
        
        try:
            while self._running and self.state == ConnectionState.CONNECTED:
                try:
                    # Read header (16 bytes minimum)
                    header_data = await self.reader.readexactly(16)
                    
                    # Parse header to get payload length
                    payload_length = int.from_bytes(header_data[8:12], byteorder='big')
                    
                    # Read payload
                    payload = await self.reader.readexactly(payload_length)
                    
                    # Process message
                    message_data = header_data + payload
                    
                    # Notify event handlers
                    self._notify_event('data', message_data)
                    
                    # Process using protocol handler
                    self.protocol.process_received_data(message_data)
                    
                except asyncio.IncompleteReadError:
                    # Connection closed
                    break
                    
        except Exception as e:
            if self._running:
                self.last_error = e
                logger.error(f"Receive failed: {e}")
                
                # Connection might be lost, try to reconnect
                if self.options["reconnect"]:
                    self.state = ConnectionState.RECONNECTING
                    asyncio.create_task(self._connect_internal())
                else:
                    self.state = ConnectionState.ERROR
                    
                    # Notify event handlers
                    self._notify_event('error', e)
        
        if self._running and self.state != ConnectionState.DISCONNECTING:
            # Connection was lost, not an intentional disconnect
            self.state = ConnectionState.DISCONNECTED
            
            # Notify event handlers
            self._notify_event('disconnected')
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context for secure connections.
        
        Returns:
            SSL context
        """
        # Create context
        if self.endpoint_type == EndpointType.SERVER:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # Load server certificate and key
            if self.options["tls_cert_file"] and self.options["tls_key_file"]:
                ssl_context.load_cert_chain(
                    self.options["tls_cert_file"],
                    self.options["tls_key_file"]
                )
            
            # Verify client certificates if needed
            if self.options["tls_verify"] and self.options["tls_ca_file"]:
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                ssl_context.load_verify_locations(self.options["tls_ca_file"])
                
        else:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Load client certificate and key if needed
            if self.options["tls_cert_file"] and self.options["tls_key_file"]:
                ssl_context.load_cert_chain(
                    self.options["tls_cert_file"],
                    self.options["tls_key_file"]
                )
            
            # Verify server certificate
            if self.options["tls_verify"]:
                ssl_context.check_hostname = True
                if self.options["tls_ca_file"]:
                    ssl_context.load_verify_locations(self.options["tls_ca_file"])
            else:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        
        return ssl_context
    
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
    
    def get_connection_state(self) -> ConnectionState:
        """
        Get the current connection state.
        
        Returns:
            Connection state
        """
        return self.state
    
    def get_local_address(self) -> Optional[Tuple[str, int]]:
        """
        Get the local address.
        
        Returns:
            Local address as (host, port), or None if not connected
        """
        if self.writer:
            return self.writer.get_extra_info('sockname')
        return None
    
    def get_remote_address(self) -> Optional[Tuple[str, int]]:
        """
        Get the remote address.
        
        Returns:
            Remote address as (host, port), or None if not connected
        """
        if self.writer:
            return self.writer.get_extra_info('peername')
        return None
    
    def is_connected(self) -> bool:
        """
        Check if the endpoint is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self.state == ConnectionState.CONNECTED
    
    def get_client_count(self) -> int:
        """
        Get the number of connected clients (server mode).
        
        Returns:
            Number of connected clients
        """
        return len(self.clients)
    
    def get_option(self, name: str) -> Any:
        """
        Get an option value.
        
        Args:
            name: Option name
        
        Returns:
            Option value, or None if not found
        """
        return self.options.get(name)
    
    def set_option(self, name: str, value: Any) -> None:
        """
        Set an option value.
        
        Args:
            name: Option name
            value: Option value
        """
        self.options[name] = value