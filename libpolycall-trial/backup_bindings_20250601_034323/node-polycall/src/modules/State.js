// State.js - PolyCall State Implementation
const EventEmitter = require('events');

class State extends EventEmitter {
    constructor(name, options = {}) {
        super();
        
        // Ensure name is a string and not empty
        if (!name || typeof name !== 'string') {
            throw new Error('State name must be a non-empty string');
        }
        
        this.name = name;
        this.isLocked = false;
        this.handlers = new Map();
        this.metadata = new Map();
        this.transitions = new Set();
        
        // Safely create endpoint from name
        const defaultEndpoint = `/${name.trim().toLowerCase().replace(/\s+/g, '-')}`;
        this.endpoint = options.endpoint || defaultEndpoint;
        
        this.timeout = options.timeout || 5000;
        this.retryCount = options.retryCount || 3;
        
        // Initialize state metadata
        this.metadata.set('createdAt', Date.now());
        this.metadata.set('version', 1);
        this.metadata.set('lastModified', Date.now());
    }
    // Handler management
    addHandler(event, handler) {
        if (typeof handler !== 'function') {
            throw new Error('Handler must be a function');
        }
        this.handlers.set(event, handler);
        return this;
    }

    removeHandler(event) {
        this.handlers.delete(event);
        return this;
    }

    async executeHandler(event, ...args) {
        if (this.isLocked) {
            throw new Error(`State ${this.name} is locked`);
        }

        const handler = this.handlers.get(event);
        if (!handler) {
            throw new Error(`No handler found for event ${event} in state ${this.name}`);
        }

        try {
            return await handler.apply(this, args);
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    // State locking
    lock() {
        if (this.isLocked) {
            throw new Error(`State ${this.name} is already locked`);
        }
        this.isLocked = true;
        this.metadata.set('lockedAt', Date.now());
        this.emit('locked');
        return this;
    }

    unlock() {
        if (!this.isLocked) {
            throw new Error(`State ${this.name} is not locked`);
        }
        this.isLocked = false;
        this.metadata.delete('lockedAt');
        this.emit('unlocked');
        return this;
    }

    // Transition management
    addTransition(toState) {
        this.transitions.add(toState);
        return this;
    }

    canTransitionTo(targetState) {
        return this.transitions.has(targetState);
    }

    // Endpoint management
    getEndpoint() {
        return this.endpoint;
    }

    setEndpoint(endpoint) {
        if (typeof endpoint !== 'string' || !endpoint.startsWith('/')) {
            throw new Error('Endpoint must be a string starting with /');
        }
        this.endpoint = endpoint;
        return this;
    }

    // State verification
    verify() {
        return {
            name: this.name,
            isLocked: this.isLocked,
            handlerCount: this.handlers.size,
            transitionCount: this.transitions.size,
            metadata: Object.fromEntries(this.metadata),
            endpoint: this.endpoint
        };
    }

    // Metadata management
    setMetadata(key, value) {
        this.metadata.set(key, value);
        this.metadata.set('lastModified', Date.now());
        this.metadata.set('version', (this.metadata.get('version') || 0) + 1);
        return this;
    }

    getMetadata(key) {
        return this.metadata.get(key);
    }

    // Serialization
    toJSON() {
        return {
            name: this.name,
            isLocked: this.isLocked,
            endpoint: this.endpoint,
            metadata: Object.fromEntries(this.metadata),
            transitions: Array.from(this.transitions)
        };
    }

    // Create state snapshot
    createSnapshot() {
        return {
            timestamp: Date.now(),
            state: this.toJSON(),
            checksum: this.calculateStateChecksum()
        };
    }

    // Restore from snapshot
    restoreFromSnapshot(snapshot) {
        if (!snapshot || !snapshot.state || !snapshot.checksum) {
            throw new Error('Invalid snapshot format');
        }

        if (snapshot.checksum !== this.calculateStateChecksum(snapshot.state)) {
            throw new Error('Snapshot checksum verification failed');
        }

        this.name = snapshot.state.name;
        this.isLocked = snapshot.state.isLocked;
        this.endpoint = snapshot.state.endpoint;
        this.metadata = new Map(Object.entries(snapshot.state.metadata));
        this.transitions = new Set(snapshot.state.transitions);

        this.emit('restored', snapshot);
        return this;
    }

    // Calculate state checksum
    calculateStateChecksum(stateData = this.toJSON()) {
        let checksum = 0;
        const stateString = JSON.stringify(stateData);
        
        for (let i = 0; i < stateString.length; i++) {
            checksum = ((checksum << 5) - checksum) + stateString.charCodeAt(i);
            checksum = checksum & checksum; // Convert to 32-bit integer
        }
        
        return checksum >>> 0; // Convert to unsigned
    }
}

module.exports = State;