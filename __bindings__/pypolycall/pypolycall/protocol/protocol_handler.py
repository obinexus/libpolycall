"""
Protocol handler for PyPolyCall.

This module implements the protocol handler for communication with LibPolyCall,
handling message encoding/decoding, checksums, and message processing.
"""

import struct
import time
import zlib
import asyncio
import logging
from typing import Dict, Optional, List, Callable, Any, Union, Tuple, Set, cast
from dataclasses import dataclass
from enum import IntEnum

from ..core.types import (
    MessageType, ProtocolFlags, ProtocolState, MessageHeader,
    CoreError, ErrorSource, PolyCallException
)
from ..core.error import set_error, check_params, throw_if_error
from ..core.context import CoreContext

# Configure logger
logger = logging.getLogger("pypolycall.protocol")

# Protocol constants
PROTOCOL_VERSION = 1
PROTOCOL_MAGIC = 0x504C43  # "PLC"
PROTOCOL_HEADER_SIZE = 16
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB
DEFAULT_TIMEOUT = 5000  # ms


@dataclass
class ProtocolMessage:
    """Protocol message container."""
    header: MessageHeader
    payload: bytes
    
    def to_bytes(self) -> bytes:
        """Convert message to byte representation."""
        return self.header.to_bytes() + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ProtocolMessage':
        """Create message from byte representation."""
        if len(data) < PROTOCOL_HEADER_SIZE:
            raise ValueError("Message data too short")
        
        header = MessageHeader.from_bytes(data[:PROTOCOL_HEADER_SIZE])
        payload = data[PROTOCOL_HEADER_SIZE:]
        
        if len(payload) != header.payload_length:
            raise ValueError(f"Payload length mismatch: expected {header.payload_length}, got {len(payload)}")
        
        return cls(header=header, payload=payload)
    
    def verify_checksum(self) -> bool:
        """Verify message checksum."""
        return self.header.checksum == calculate_checksum(self.payload)


class PendingMessage:
    """Container for a pending message with response handling."""
    
    def __init__(self, message: ProtocolMessage, timeout_ms: int = DEFAULT_TIMEOUT):
        """
        Initialize a pending message.
        
        Args:
            message: Protocol message
            timeout_ms: Timeout in milliseconds
        """
        self.message = message
        self.timeout_ms = timeout_ms
        self.future: asyncio.Future = asyncio.Future()
        self.timestamp = time.time()
    
    def is_expired(self) -> bool:
        """Check if the message has expired."""
        return time.time() - self.timestamp > (self.timeout_ms / 1000)
    
    def complete(self, response: ProtocolMessage) -> None:
        """Complete the pending message with a response."""
        if not self.future.done():
            self.future.set_result(response)
    
    def complete_with_error(self, error: Exception) -> None:
        """Complete the pending message with an error."""
        if not self.future.done():
            self.future.set_exception(error)
    
    async def wait_for_response(self) -> ProtocolMessage:
        """Wait for a response to the message."""
        return await self.future


class ProtocolHandler:
    """Protocol handler for LibPolyCall communication."""
    
    def __init__(
        self,
        core_ctx: CoreContext,
        protocol_version: int = PROTOCOL_VERSION,
        checksum_algorithm: str = 'crc32'
    ):
        """
        Initialize the protocol handler.
        
        Args:
            core_ctx: Core context
            protocol_version: Protocol version
            checksum_algorithm: Checksum algorithm to use
        """
        self.core_ctx = core_ctx
        self.version = protocol_version
        self.checksum_algorithm = checksum_algorithm
        self.state = ProtocolState.INIT
        self.sequence = 1
        self.pending_messages: Dict[int, PendingMessage] = {}
        self.handlers: Dict[MessageType, List[Callable[[ProtocolMessage], Any]]] = {
            msg_type: [] for msg_type in MessageType
        }
        self.encryption_enabled = False
        self.compression_enabled = False
        
        # Event for notifying message processors
        self._message_event = asyncio.Event()
        self._incoming_queue: List[ProtocolMessage] = []
        self._outgoing_queue: List[ProtocolMessage] = []
        
        # Processing task
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Last activity timestamp
        self.last_heartbeat = 0.0
        self.handshake_complete = False
        self.authenticated = False
    
    def start(self) -> None:
        """Start the protocol handler processing tasks."""
        if not self._running:
            self._running = True
            self._processing_task = asyncio.create_task(self._process_messages())
    
    def stop(self) -> None:
        """Stop the protocol handler."""
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
    
    async def _process_messages(self) -> None:
        """Process incoming and outgoing messages."""
        while self._running:
            # Process incoming messages
            while self._incoming_queue:
                message = self._incoming_queue.pop(0)
                await self._handle_message(message)
            
            # Process outgoing messages
            while self._outgoing_queue:
                message = self._outgoing_queue.pop(0)
                # This would call a send method on a transport
                # For now, we'll just log it
                logger.debug(f"Would send message: {message}")
            
            # Check for expired messages
            expired_sequences = []
            for seq, pending in self.pending_messages.items():
                if pending.is_expired():
                    pending.complete_with_error(
                        PolyCallException(CoreError.TIMEOUT, "Message timeout")
                    )
                    expired_sequences.append(seq)
            
            for seq in expired_sequences:
                del self.pending_messages[seq]
            
            # Wait for more messages
            try:
                await asyncio.wait_for(self._message_event.wait(), 0.1)
                self._message_event.clear()
            except asyncio.TimeoutError:
                pass
    
    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[ProtocolMessage], Any]
    ) -> None:
        """
        Register a message handler.
        
        Args:
            message_type: Message type to handle
            handler: Handler function
        """
        self.handlers[message_type].append(handler)
    
    def unregister_handler(
        self,
        message_type: MessageType,
        handler: Callable[[ProtocolMessage], Any]
    ) -> bool:
        """
        Unregister a message handler.
        
        Args:
            message_type: Message type
            handler: Handler function to unregister
        
        Returns:
            True if the handler was found and removed, False otherwise
        """
        if message_type in self.handlers:
            try:
                self.handlers[message_type].remove(handler)
                return True
            except ValueError:
                return False
        return False
    
    async def send_message(
        self,
        message_type: MessageType,
        payload: Union[bytes, str],
        flags: ProtocolFlags = ProtocolFlags.NONE,
        timeout_ms: int = DEFAULT_TIMEOUT
    ) -> ProtocolMessage:
        """
        Send a message and wait for a response.
        
        Args:
            message_type: Message type
            payload: Message payload
            flags: Message flags
            timeout_ms: Timeout in milliseconds
        
        Returns:
            Response message
        """
        # Convert string to bytes if needed
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # Apply compression if enabled and requested
        if self.compression_enabled and (flags & ProtocolFlags.COMPRESSED):
            payload = zlib.compress(payload)
        
        # Apply encryption if enabled and requested
        if self.encryption_enabled and (flags & ProtocolFlags.ENCRYPTED):
            # Encryption would be applied here
            pass
        
        # Create message
        message = self._create_message(message_type, payload, flags)
        
        # Create pending message
        pending = PendingMessage(message, timeout_ms)
        
        # Store in pending messages
        self.pending_messages[message.header.sequence] = pending
        
        # Add to outgoing queue
        self._outgoing_queue.append(message)
        self._message_event.set()
        
        # Wait for response
        return await pending.wait_for_response()
    
    def process_received_data(self, data: bytes) -> None:
        """
        Process received data.
        
        Args:
            data: Received data
        """
        if len(data) < PROTOCOL_HEADER_SIZE:
            logger.warning(f"Received data too short: {len(data)} bytes")
            return
        
        try:
            # Parse message
            message = ProtocolMessage.from_bytes(data)
            
            # Verify checksum
            if not message.verify_checksum():
                logger.warning("Checksum verification failed")
                return
            
            # Add to incoming queue
            self._incoming_queue.append(message)
            self._message_event.set()
            
        except Exception as e:
            logger.error(f"Error processing received data: {e}")
    
    async def _handle_message(self, message: ProtocolMessage) -> None:
        """
        Handle a received message.
        
        Args:
            message: Protocol message
        """
        message_type = message.header.type
        
        # Check if this is a response to a pending message
        if message_type == MessageType.RESPONSE:
            sequence = message.header.sequence
            if sequence in self.pending_messages:
                pending = self.pending_messages.pop(sequence)
                pending.complete(message)
                return
        
        # Handle message based on type
        if message_type == MessageType.HANDSHAKE:
            await self._handle_handshake(message)
        elif message_type == MessageType.AUTH:
            await self._handle_auth(message)
        elif message_type == MessageType.COMMAND:
            await self._handle_command(message)
        elif message_type == MessageType.ERROR:
            await self._handle_error(message)
        elif message_type == MessageType.HEARTBEAT:
            await self._handle_heartbeat(message)
        
        # Call registered handlers
        for handler in self.handlers.get(message_type, []):
            try:
                await asyncio.coroutine(handler)(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    async def _handle_handshake(self, message: ProtocolMessage) -> None:
        """
        Handle a handshake message.
        
        Args:
            message: Handshake message
        """
        try:
            # Check protocol magic
            if len(message.payload) >= 4:
                magic = struct.unpack("!I", message.payload[:4])[0]
                if magic != PROTOCOL_MAGIC:
                    logger.warning(f"Invalid protocol magic: 0x{magic:x}")
                    return
            
            # Mark handshake as complete
            self.handshake_complete = True
            self.state = ProtocolState.HANDSHAKE
            
            # Create response
            response = self._create_message(
                MessageType.HANDSHAKE,
                b'',
                ProtocolFlags.RELIABLE
            )
            
            # Add to outgoing queue
            self._outgoing_queue.append(response)
            self._message_event.set()
            
            logger.info("Handshake completed")
            
        except Exception as e:
            logger.error(f"Error handling handshake: {e}")
    
    async def _handle_auth(self, message: ProtocolMessage) -> None:
        """
        Handle an auth message.
        
        Args:
            message: Auth message
        """
        try:
            # Auth implementation would go here
            
            # Mark as authenticated
            self.authenticated = True
            self.state = ProtocolState.AUTH
            
            # Create response
            response = self._create_message(
                MessageType.RESPONSE,
                b'{"status":"authenticated"}',
                message.header.flags,
                message.header.sequence
            )
            
            # Add to outgoing queue
            self._outgoing_queue.append(response)
            self._message_event.set()
            
            logger.info("Authentication completed")
            
        except Exception as e:
            logger.error(f"Error handling auth: {e}")
    
    async def _handle_command(self, message: ProtocolMessage) -> None:
        """
        Handle a command message.
        
        Args:
            message: Command message
        """
        try:
            # Process command
            command_data = message.payload.decode('utf-8')
            
            # Create response
            response = self._create_message(
                MessageType.RESPONSE,
                f'{{"status":"ok","command":{command_data}}}'.encode('utf-8'),
                message.header.flags,
                message.header.sequence
            )
            
            # Add to outgoing queue
            self._outgoing_queue.append(response)
            self._message_event.set()
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            
            # Create error response
            error_response = self._create_message(
                MessageType.ERROR,
                f'{{"error":"Command processing failed: {str(e)}"}}'.encode('utf-8'),
                message.header.flags,
                message.header.sequence
            )
            
            # Add to outgoing queue
            self._outgoing_queue.append(error_response)
            self._message_event.set()
    
    async def _handle_error(self, message: ProtocolMessage) -> None:
        """
        Handle an error message.
        
        Args:
            message: Error message
        """
        try:
            error_data = message.payload.decode('utf-8')
            logger.error(f"Received error: {error_data}")
            
            # Set protocol state to error
            self.state = ProtocolState.ERROR
            
            # If this is a response to a pending message, complete it with error
            sequence = message.header.sequence
            if sequence in self.pending_messages:
                pending = self.pending_messages.pop(sequence)
                pending.complete_with_error(
                    PolyCallException(CoreError.PROTOCOL, error_data)
                )
            
        except Exception as e:
            logger.error(f"Error handling error message: {e}")
    
    async def _handle_heartbeat(self, message: ProtocolMessage) -> None:
        """
        Handle a heartbeat message.
        
        Args:
            message: Heartbeat message
        """
        try:
            # Update last heartbeat time
            self.last_heartbeat = time.time()
            
            # Create response
            response = self._create_message(
                MessageType.HEARTBEAT,
                b'',
                message.header.flags,
                message.header.sequence
            )
            
            # Add to outgoing queue
            self._outgoing_queue.append(response)
            self._message_event.set()
            
        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")
    
    def _create_message(
        self,
        message_type: MessageType,
        payload: bytes,
        flags: ProtocolFlags = ProtocolFlags.NONE,
        sequence: Optional[int] = None
    ) -> ProtocolMessage:
        """
        Create a new protocol message.
        
        Args:
            message_type: Message type
            payload: Message payload
            flags: Message flags
            sequence: Message sequence number (auto-generated if None)
        
        Returns:
            Protocol message
        """
        # Use provided sequence or generate a new one
        if sequence is None:
            sequence = self.sequence
            self.sequence += 1
        
        # Calculate checksum
        checksum = calculate_checksum(payload)
        
        # Create header
        header = MessageHeader(
            version=self.version,
            type=message_type,
            flags=flags,
            sequence=sequence,
            payload_length=len(payload),
            checksum=checksum
        )
        
        return ProtocolMessage(header=header, payload=payload)
    
    def reset(self) -> None:
        """Reset the protocol handler state."""
        self.state = ProtocolState.INIT
        self.handshake_complete = False
        self.authenticated = False
        self.sequence = 1
        
        # Clear pending messages
        for pending in self.pending_messages.values():
            pending.complete_with_error(
                PolyCallException(CoreError.CANCELED, "Protocol reset")
            )
        
        self.pending_messages.clear()
        self._incoming_queue.clear()
        self._outgoing_queue.clear()
    
    async def start_handshake(self) -> None:
        """Initiate a handshake with the server."""
        # Create handshake message
        payload = struct.pack("!I", PROTOCOL_MAGIC)
        
        # Send handshake message
        await self.send_message(
            MessageType.HANDSHAKE,
            payload,
            ProtocolFlags.RELIABLE
        )
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with the server.
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            True if authentication succeeded, False otherwise
        """
        import json
        
        # Check if handshake is complete
        if not self.handshake_complete:
            raise PolyCallException(
                CoreError.INVALID_STATE,
                "Handshake not complete"
            )
        
        # Create auth message
        payload = json.dumps(credentials).encode('utf-8')
        
        try:
            # Send auth message
            response = await self.send_message(
                MessageType.AUTH,
                payload,
                ProtocolFlags.ENCRYPTED | ProtocolFlags.RELIABLE
            )
            
            # Check response
            response_data = json.loads(response.payload.decode('utf-8'))
            
            # Update state if authentication succeeded
            if response_data.get("status") == "authenticated":
                self.authenticated = True
                self.state = ProtocolState.READY
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def can_transition(self, target_state: ProtocolState) -> bool:
        """
        Check if the protocol can transition to a target state.
        
        Args:
            target_state: Target state
        
        Returns:
            True if transition is valid, False otherwise
        """
        # Define valid transitions
        valid_transitions = {
            ProtocolState.INIT: {ProtocolState.HANDSHAKE},
            ProtocolState.HANDSHAKE: {ProtocolState.AUTH, ProtocolState.ERROR},
            ProtocolState.AUTH: {ProtocolState.READY, ProtocolState.ERROR},
            ProtocolState.READY: {ProtocolState.CLOSED, ProtocolState.ERROR},
            ProtocolState.ERROR: {ProtocolState.INIT, ProtocolState.CLOSED},
            ProtocolState.CLOSED: {ProtocolState.INIT}
        }
        
        # Check if transition is valid
        return target_state in valid_transitions.get(self.state, set())
    
    def transition_to(self, target_state: ProtocolState) -> bool:
        """
        Transition to a target state.
        
        Args:
            target_state: Target state
        
        Returns:
            True if transition succeeded, False otherwise
        """
        if not self.can_transition(target_state):
            logger.warning(f"Invalid state transition: {self.state.name} -> {target_state.name}")
            return False
        
        # Perform transition
        old_state = self.state
        self.state = target_state
        
        logger.info(f"Protocol state transitioned: {old_state.name} -> {target_state.name}")
        return True
    
    def get_state(self) -> ProtocolState:
        """
        Get the current protocol state.
        
        Returns:
            Current protocol state
        """
        return self.state
    
    def is_connected(self) -> bool:
        """
        Check if the protocol is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self.state in {ProtocolState.HANDSHAKE, ProtocolState.AUTH, ProtocolState.READY}
    
    def is_authenticated(self) -> bool:
        """
        Check if the protocol is authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.state in {ProtocolState.AUTH, ProtocolState.READY}
    
    def is_ready(self) -> bool:
        """
        Check if the protocol is ready for commands.
        
        Returns:
            True if ready, False otherwise
        """
        return self.state == ProtocolState.READY


def calculate_checksum(data: bytes) -> int:
    """
    Calculate checksum for data.
    
    Args:
        data: Data to calculate checksum for
    
    Returns:
        Checksum value
    """
    return zlib.crc32(data) & 0xFFFFFFFF