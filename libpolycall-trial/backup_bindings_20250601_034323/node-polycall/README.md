# libpolycall Node.js Bindings

## Overview

`libpolycall` is a comprehensive library designed to facilitate data-oriented programming interfaces. This repository provides Node.js bindings for `libpolycall`, enabling seamless integration with Node.js applications.

## Features

- **Protocol Handling**: Manage communication protocols with ease.
- **State Management**: Implement state machines with robust state transitions.
- **Network Communication**: Handle network endpoints and client connections.
- **Checksum Calculation**: Ensure data integrity with checksum utilities.

## Installation

To install the `libpolycall` Node.js bindings, run:

```sh
npm install @obinexuscomputing/node-polycall
```

## Usage

### Basic Example

```js
const { PolyCallClient, MESSAGE_TYPES, PROTOCOL_FLAGS } = require('node-polycall');

async function main() {
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

        const states = await client.getAllStates();
        console.log('Current states:', states);

        await client.transitionTo('ready');

        const result = await client.executeCommand('status');
        console.log('Command result:', result);
    } catch (error) {
        console.error('Error:', error);
    }
}

main();
```

### API Reference

#### PolyCallClient

- **connect()**: Connect to the PolyCall server.
- **disconnect()**: Disconnect from the PolyCall server.
- **sendRequest(path, method, data)**: Send a request to the server.
- **executeCommand(command, data)**: Execute a command on the server.
- **transitionTo(stateName)**: Transition to a specified state.
- **authenticate(credentials)**: Authenticate with the server.
- **isConnected()**: Check if connected to the server.
- **isAuthenticated()**: Check if authenticated with the server.
- **getCurrentState()**: Get the current state.
- **getStateHistory()**: Get the state history.
- **getState(stateName)**: Get a specific state.
- **getAllStates()**: Get all states.
- **lockState(stateName)**: Lock a specific state.
- **unlockState(stateName)**: Unlock a specific state.

## Development

### Building from Source

To build the Node.js bindings from source, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://gitlab.com/obinexuscomputing/libpolycall.git
    cd libpolycall/bindings/node-polycall
    ```

2. Install dependencies:
    ```sh
    npm install
    ```

3. Build the project:
    ```sh
    npm run build
    ```

### Running Tests

To run the tests, use:

```sh
npm test
```

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

Special thanks to the contributors and the open-source community for their support and contributions.
