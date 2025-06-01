// ProtocolHandler.js - PolyCall Protocol Implementation
const EventEmitter = require('events');
const crypto = require('crypto');

const PROTOCOL_CONSTANTS = {
    VERSION: 1,
    MAGIC: 0x504C43, // "PLC"
    HEADER_SIZE: 16,
    MAX_PAYLOAD_SIZE: 1024 * 1024, // 1MB
    DEFAULT_TIMEOUT: 5000
};

const MESSAGE_TYPES = {
    HANDSHAKE: 0x01,
    AUTH: 0x02,
    COMMAND: 0x03,
    RESPONSE: 0x04,
    ERROR: 0x05,
    HEARTBEAT: 0x06
};

const PROTOCOL_FLAGS = {
    NONE: 0x00,
    ENCRYPTED: 0x01,
    COMPRESSED: 0x02,
    URGENT: 0x04,
    RELIABLE: 0x08
};

class ProtocolHandler extends EventEmitter {
    constructor(options = {}) {
        super();
        this.version = options.version || PROTOCOL_CONSTANTS.VERSION;
        this.checksumAlgorithm = options.checksumAlgorithm || 'sha256';
        this.sequence = 1;
        this.pendingMessages = new Map();
        this.encryptionEnabled = options.encryption || false;
        this.compressionEnabled = options.compression || false;
        
        // Message processing queues
        this.incomingQueue = [];
        this.outgoingQueue = [];
        
        // Initialize protocol state
        this.reset();
    }

    // Protocol state management
    reset() {
        this.handshakeComplete = false;
        this.authenticated = false;
        this.lastHeartbeat = null;
        this.sequence = 1;
        this.pendingMessages.clear();
        this.incomingQueue = [];
        this.outgoingQueue = [];
    }

    // Header creation and validation
    createHeader(type, payloadLength, flags = PROTOCOL_FLAGS.NONE) {
        const header = Buffer.alloc(PROTOCOL_CONSTANTS.HEADER_SIZE);
        
        header.writeUInt8(this.version, 0); // Version
        header.writeUInt8(type, 1); // Message type
        header.writeUInt16LE(flags, 2); // Flags
        header.writeUInt32LE(this.sequence++, 4); // Sequence number
        header.writeUInt32LE(payloadLength, 8); // Payload length
        header.writeUInt32LE(0, 12); // Checksum placeholder
        
        return header;
    }

    validateHeader(header) {
        if (!header || header.length !== PROTOCOL_CONSTANTS.HEADER_SIZE) {
            throw new Error('Invalid header size');
        }

        const version = header.readUInt8(0);
        if (version !== this.version) {
            throw new Error(`Protocol version mismatch: expected ${this.version}, got ${version}`);
        }

        const payloadLength = header.readUInt32LE(8);
        if (payloadLength > PROTOCOL_CONSTANTS.MAX_PAYLOAD_SIZE) {
            throw new Error('Payload size exceeds maximum allowed');
        }

        return {
            version,
            type: header.readUInt8(1),
            flags: header.readUInt16LE(2),
            sequence: header.readUInt32LE(4),
            payloadLength,
            checksum: header.readUInt32LE(12)
        };
    }

    // Message creation and processing
    createMessage(type, payload, flags = PROTOCOL_FLAGS.NONE) {
        const payloadBuffer = Buffer.from(payload);
        const header = this.createHeader(type, payloadBuffer.length, flags);
        const checksum = this.calculateChecksum(payloadBuffer);
        
        header.writeUInt32LE(checksum, 12); // Set checksum in header
        
        return Buffer.concat([header, payloadBuffer]);
    }

    async processMessage(data) {
        try {
            if (data.length < PROTOCOL_CONSTANTS.HEADER_SIZE) {
                throw new Error('Message too short');
            }

            const header = this.validateHeader(data.slice(0, PROTOCOL_CONSTANTS.HEADER_SIZE));
            const payload = data.slice(PROTOCOL_CONSTANTS.HEADER_SIZE);

            if (payload.length !== header.payloadLength) {
                throw new Error('Payload length mismatch');
            }

            const calculatedChecksum = this.calculateChecksum(payload);
            if (calculatedChecksum !== header.checksum) {
                throw new Error('Checksum verification failed');
            }

            return await this.handleMessage(header, payload);
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    // Message type handlers
    async handleMessage(header, payload) {
        switch (header.type) {
            case MESSAGE_TYPES.HANDSHAKE:
                return await this.handleHandshake(header, payload);
            case MESSAGE_TYPES.AUTH:
                return await this.handleAuth(header, payload);
            case MESSAGE_TYPES.COMMAND:
                return await this.handleCommand(header, payload);
            case MESSAGE_TYPES.RESPONSE:
                return await this.handleResponse(header, payload);
            case MESSAGE_TYPES.ERROR:
                return await this.handleError(header, payload);
            case MESSAGE_TYPES.HEARTBEAT:
                return await this.handleHeartbeat(header, payload);
            default:
                throw new Error(`Unknown message type: ${header.type}`);
        }
    }

    // Specific message handlers
    async handleHandshake(header, payload) {
        const magic = payload.readUInt32LE(0);
        if (magic !== PROTOCOL_CONSTANTS.MAGIC) {
            throw new Error('Invalid protocol magic number');
        }

        this.handshakeComplete = true;
        this.emit('handshake', { sequence: header.sequence });
        
        return this.createMessage(MESSAGE_TYPES.HANDSHAKE, Buffer.alloc(0), PROTOCOL_FLAGS.RELIABLE);
    }

    async handleAuth(header, payload) {
        // Auth implementation would go here
        this.authenticated = true;
        this.emit('authenticated', { sequence: header.sequence });
    }

    async handleCommand(header, payload) {
        this.emit('command', {
            sequence: header.sequence,
            command: payload.toString(),
            flags: header.flags
        });
    }

    async handleResponse(header, payload) {
        const pending = this.pendingMessages.get(header.sequence);
        if (pending) {
            this.pendingMessages.delete(header.sequence);
            pending.resolve(payload);
        }
        this.emit('response', { sequence: header.sequence, payload });
    }

    async handleError(header, payload) {
        const pending = this.pendingMessages.get(header.sequence);
        if (pending) {
            this.pendingMessages.delete(header.sequence);
            pending.reject(new Error(payload.toString()));
        }
        this.emit('error', { sequence: header.sequence, error: payload.toString() });
    }

    async handleHeartbeat(header) {
        this.lastHeartbeat = Date.now();
        this.emit('heartbeat', { sequence: header.sequence, timestamp: this.lastHeartbeat });
    }

    // Utility functions
    calculateChecksum(data) {
        if (typeof data === 'string') {
            data = Buffer.from(data);
        }
        
        let checksum = 0;
        for (let i = 0; i < data.length; i++) {
            checksum = ((checksum << 5) | (checksum >>> 27)) + data[i];
        }
        return checksum >>> 0; // Convert to unsigned 32-bit
    }

    // Message sending with promise-based response handling
    async sendMessage(type, payload, flags = PROTOCOL_FLAGS.NONE) {
        const message = this.createMessage(type, payload, flags);
        const sequence = message.readUInt32LE(4);

        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                this.pendingMessages.delete(sequence);
                reject(new Error('Message timeout'));
            }, PROTOCOL_CONSTANTS.DEFAULT_TIMEOUT);

            this.pendingMessages.set(sequence, { resolve, reject, timeout });
            this.emit('send', message);
        });
    }

    // Protocol verification
    verifyMessage(data) {
        try {
            const header = this.validateHeader(data.slice(0, PROTOCOL_CONSTANTS.HEADER_SIZE));
            const payload = data.slice(PROTOCOL_CONSTANTS.HEADER_SIZE);
            const calculatedChecksum = this.calculateChecksum(payload);
            
            return calculatedChecksum === header.checksum;
        } catch (error) {
            return false;
        }
    }
}

module.exports = {
    ProtocolHandler,
    PROTOCOL_CONSTANTS,
    MESSAGE_TYPES,
    PROTOCOL_FLAGS
};