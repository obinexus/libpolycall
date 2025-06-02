// NetworkEndpoint.js - PolyCall Network Endpoint Implementation
const net = require('net');
const EventEmitter = require('events');
const { ProtocolHandler } = require('./ProtocolHandler');

class NetworkEndpoint extends EventEmitter {
    constructor(options = {}) {
        super();
        this.options = {
            host: 'localhost',
            port: 8080,
            backlog: 1024,
            timeout: 5000,
            keepAlive: true,
            reconnect: true,
            maxRetries: 3,
            retryDelay: 1000,
            ...options
        };

        this.socket = null;
        this.server = null;
        this.protocol = new ProtocolHandler(options);
        this.connected = false;
        this.retryCount = 0;
        this.pendingData = [];

        // Protocol event handling
        this.protocol.on('send', (data) => this.send(data));
        this.protocol.on('error', (error) => this.emit('error', error));
    }

    // Server operations
    async listen() {
        return new Promise((resolve, reject) => {
            try {
                this.server = net.createServer((socket) => {
                    this.handleConnection(socket);
                });

                this.server.on('error', (error) => {
                    this.emit('error', error);
                    reject(error);
                });

                this.server.listen(this.options.port, this.options.host, () => {
                    this.emit('listening', {
                        address: this.server.address(),
                        endpoint: this
                    });
                    resolve(this);
                });

            } catch (error) {
                reject(error);
            }
        });
    }

    async close() {
        return new Promise((resolve) => {
            if (this.server) {
                this.server.close(() => {
                    this.server = null;
                    this.emit('server:closed');
                    resolve();
                });
            } else {
                resolve();
            }
        });
    }

    // Client operations
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.socket = new net.Socket();

                this.socket.on('connect', () => {
                    this.connected = true;
                    this.retryCount = 0;
                    this.emit('connected');

                    // Process any pending data
                    while (this.pendingData.length > 0) {
                        const data = this.pendingData.shift();
                        this.send(data);
                    }

                    resolve(this);
                });

                this.socket.on('data', (data) => {
                    this.handleData(data);
                });

                this.socket.on('close', () => {
                    this.handleDisconnect();
                });

                this.socket.on('error', (error) => {
                    this.emit('error', error);
                    this.handleDisconnect();
                    reject(error);
                });

                // Configure socket
                this.socket.setKeepAlive(this.options.keepAlive);
                this.socket.setTimeout(this.options.timeout);

                // Connect socket
                this.socket.connect({
                    host: this.options.host,
                    port: this.options.port
                });

            } catch (error) {
                reject(error);
            }
        });
    }

    async disconnect() {
        return new Promise((resolve) => {
            if (this.socket) {
                this.options.reconnect = false; // Prevent auto-reconnect
                this.socket.end(() => {
                    this.socket = null;
                    this.connected = false;
                    this.emit('disconnected');
                    resolve();
                });
            } else {
                resolve();
            }
        });
    }

    // Data transmission
    async send(data) {
        return new Promise((resolve, reject) => {
            if (!this.connected) {
                if (this.options.reconnect) {
                    this.pendingData.push(data);
                    this.connect().catch(reject);
                    return;
                }
                reject(new Error('Not connected'));
                return;
            }

            this.socket.write(data, (error) => {
                if (error) {
                    reject(error);
                } else {
                    resolve();
                }
            });
        });
    }

    // Connection handling
    handleConnection(socket) {
        this.emit('connection', { socket, endpoint: this });

        socket.on('data', (data) => {
            this.handleData(data);
        });

        socket.on('close', () => {
            this.emit('socket:closed', socket);
        });

        socket.on('error', (error) => {
            this.emit('error', error);
        });
    }

    handleData(data) {
        try {
            this.protocol.processMessage(data);
        } catch (error) {
            this.emit('error', error);
        }
    }

    handleDisconnect() {
        this.connected = false;
        this.emit('disconnected');

        // Attempt reconnection if enabled
        if (this.options.reconnect && 
            this.retryCount < this.options.maxRetries) {
            this.retryCount++;
            setTimeout(() => {
                this.emit('reconnecting', this.retryCount);
                this.connect().catch((error) => {
                    this.emit('error', error);
                });
            }, this.options.retryDelay * this.retryCount);
        }
    }

    // Utility methods
    getAddress() {
        if (this.server) {
            return this.server.address();
        }
        if (this.socket) {
            return {
                address: this.socket.remoteAddress,
                port: this.socket.remotePort
            };
        }
        return null;
    }

    isConnected() {
        return this.connected;
    }

    getProtocol() {
        return this.protocol;
    }

    toString() {
        const address = this.getAddress();
        return `NetworkEndpoint(${address ? `${address.address}:${address.port}` : 'not connected'})`;
    }
}

module.exports = NetworkEndpoint;