// PolyCallClient.js - PolyCall Client Implementation
const EventEmitter = require('events');
const NetworkEndpoint = require('./NetworkEndpoint');
const Router = require('./Router');
const StateMachine = require('./StateMachine');
const { MESSAGE_TYPES, PROTOCOL_FLAGS } = require('./ProtocolHandler');

class PolyCallClient extends EventEmitter {
    constructor(options = {}) {
        super();
        this.options = {
            host: 'localhost',
            port: 8080,
            reconnect: true,
            timeout: 5000,
            maxRetries: 3,
            ...options
        };

        // Core components
        this.endpoint = new NetworkEndpoint(this.options);
        this.router = new Router(this.options);
        this.stateMachine = new StateMachine(this.options);

        // Internal state
        this.connected = false;
        this.authenticated = false;
        this.pendingRequests = new Map();

        // Set up event handlers
        this.setupEventHandlers();

        // Add middleware
        this.router.use(this.router.loggingMiddleware());
        this.router.use(this.router.errorHandler());

        // Bind state machine
        this.router.bindStateMachine(this.stateMachine);
    }

    // Connection management
    async connect() {
        try {
            await this.endpoint.connect();
            this.connected = true;
            this.emit('connected');
            
            // Begin handshake process
            const protocol = this.endpoint.getProtocol();
            await protocol.sendMessage(
                MESSAGE_TYPES.HANDSHAKE,
                Buffer.from(''), 
                PROTOCOL_FLAGS.RELIABLE
            );
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    async disconnect() {
        try {
            await this.endpoint.disconnect();
            this.connected = false;
            this.authenticated = false;
            this.emit('disconnected');
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    // Request handling
    async sendRequest(path, method = 'GET', data = {}) {
        if (!this.connected) {
            throw new Error('Not connected to server');
        }

        try {
            const response = await this.router.handleRequest(path, method, data);
            return response;
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    // Command interface
    async executeCommand(command, data = {}) {
        if (!this.authenticated) {
            throw new Error('Not authenticated');
        }

        const protocol = this.endpoint.getProtocol();
        return protocol.sendMessage(
            MESSAGE_TYPES.COMMAND,
            JSON.stringify({ command, data }),
            PROTOCOL_FLAGS.RELIABLE
        );
    }

    // State management
    async transitionTo(stateName) {
        try {
            await this.stateMachine.executeTransition(stateName);
            await this.sendRequest(`/transition/${stateName}`, 'POST');
            return true;
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    // Authentication
    async authenticate(credentials) {
        try {
            const protocol = this.endpoint.getProtocol();
            await protocol.sendMessage(
                MESSAGE_TYPES.AUTH,
                JSON.stringify(credentials),
                PROTOCOL_FLAGS.ENCRYPTED | PROTOCOL_FLAGS.RELIABLE
            );
            this.authenticated = true;
            this.emit('authenticated');
            return true;
        } catch (error) {
            this.emit('error', error);
            throw error;
        }
    }

    // Event handling setup
    setupEventHandlers() {
        const protocol = this.endpoint.getProtocol();

        protocol.on('handshake', () => {
            this.emit('handshake');
        });

        protocol.on('authenticated', () => {
            this.authenticated = true;
            this.emit('authenticated');
        });

        protocol.on('command', (data) => {
            this.emit('command', data);
        });

        protocol.on('error', (error) => {
            this.emit('error', error);
        });

        this.endpoint.on('connected', () => {
            this.connected = true;
            this.emit('connected');
        });

        this.endpoint.on('disconnected', () => {
            this.connected = false;
            this.authenticated = false;
            this.emit('disconnected');
        });

        this.endpoint.on('error', (error) => {
            this.emit('error', error);
        });

        this.stateMachine.on('transition:complete', (from, to) => {
            this.emit('state:changed', { from: from.name, to: to.name });
        });
    }

    // Utility methods
    isConnected() {
        return this.connected;
    }

    isAuthenticated() {
        return this.authenticated;
    }

    getCurrentState() {
        return this.stateMachine.getCurrentState();
    }

    getStateHistory() {
        return this.stateMachine.getHistory();
    }

    // API convenience methods
    async getState(stateName) {
        return this.sendRequest(`/states/${stateName}`);
    }

    async getAllStates() {
        return this.sendRequest('/states');
    }

    async lockState(stateName) {
        return this.sendRequest(`/states/${stateName}/lock`, 'POST');
    }

    async unlockState(stateName) {
        return this.sendRequest(`/states/${stateName}/unlock`, 'POST');
    }

    // Debug helpers
    printRoutes() {
        this.router.printRoutes();
    }

    toString() {
        return `PolyCallClient(${this.endpoint.toString()})`;
    }
}

module.exports = PolyCallClient;

// Usage example:
async function example() {
    const client = new PolyCallClient({
        host: 'localhost',
        port: 8080
    });

    client.on('connected', () => {
        console.log('Connected to server');
    });

    client.on('authenticated', () => {
        console.log('Authenticated with server');
    });

    client.on('state:changed', ({ from, to }) => {
        console.log(`State changed from ${from} to ${to}`);
    });

    try {
        await client.connect();
        await client.authenticate({ username: 'test', password: 'test' });
        
        // Get current state
        const state = await client.getAllStates();
        console.log('Current states:', state);

        // Execute transition
        await client.transitionTo('ready');

        // Execute command
        const result = await client.executeCommand('status');
        console.log('Command result:', result);

    } catch (error) {
        console.error('Error:', error);
    }
}

// Run example if this is the main module
if (require.main === module) {
    example().catch(console.error);
}