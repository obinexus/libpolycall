# PyPolyCall

Python bindings for LibPolyCall, implementing a "program-first" approach to cross-language communication.

## Overview

PyPolyCall is a comprehensive library designed to facilitate data-oriented programming interfaces. This package provides Python bindings for the LibPolyCall library, enabling seamless integration with Python applications.

## Features

- **Protocol Handling**: Manage communication protocols with ease.
- **State Management**: Implement state machines with robust state transitions.
- **Network Communication**: Handle network endpoints and client connections.
- **Zero-Trust Security**: Implements security best practices with TLS support.
- **Async/Await Support**: Fully asynchronous API for modern Python applications.

## Installation

To install PyPolyCall, use pip:

```bash
pip install pypolycall
```

## Quick Start

```python
import asyncio
from pypolycall import create_client, PolyCallException

async def main():
    # Create a client instance
    client = create_client({
        "host": "localhost",
        "port": 8084
    })
    
    # Set up event handlers
    client.on('connected', lambda: print("Connected to server"))
    client.on('authenticated', lambda: print("Authenticated with server"))
    client.on('error', lambda error: print(f"Error: {error}"))
    
    try:
        # Connect to the server
        await client.connect()
        
        # Authenticate
        await client.authenticate({
            "username": "test",
            "password": "test"
        })
        
        # Execute a command
        result = await client.execute_command("status")
        print("Command result:", result)
        
        # Disconnect
        await client.disconnect()
        
    except PolyCallException as e:
        print(f"PolyCall error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### PolyCallClient

- **connect()**: Connect to the LibPolyCall server.
- **disconnect()**: Disconnect from the server.
- **authenticate(credentials)**: Authenticate with the server.
- **execute_command(command, data)**: Execute a command on the server.
- **send_request(path, method, data)**: Send a request to a specific path.
- **get_state(state_name)**: Get a specific state.
- **get_all_states()**: Get all states.
- **lock_state(state_name)**: Lock a specific state.
- **unlock_state(state_name)**: Unlock a specific state.
- **transition_to(state_name)**: Transition to a specific state.

### Event Handling

You can register event handlers with the `on` method:

```python
client.on('connected', lambda: print("Connected"))
client.on('disconnected', lambda: print("Disconnected"))
client.on('authenticated', lambda: print("Authenticated"))
client.on('error', lambda error: print(f"Error: {error}"))
client.on('state:changed', lambda data: print(f"State changed: {data}"))
```

## Using with LibPolyCall

PyPolyCall is designed to work seamlessly with the LibPolyCall system. To use it with an existing LibPolyCall installation:

1. Start the LibPolyCall service:
   ```
   ./bin/polycall -f config.Polycallfile
   ```

2. Configure your PyPolyCall client to connect to the appropriate port (default 8084).

3. Make sure your `config.Polycallfile` includes the Python binding configuration:
   ```
   server python 3001:8084
   ```

## Advanced Usage

### Router

PyPolyCall includes a router for handling API-like requests:

```python
from pypolycall import create_client

client = create_client()
router = client.router

@router.get("/users")
async def get_users(ctx):
    return {"users": ["user1", "user2"]}

@router.post("/users")
async def create_user(ctx):
    data = ctx["data"]
    return {"created": True, "user": data}
```

### Custom Middleware

You can add custom middleware to the router:

```python
async def logging_middleware(ctx, next_middleware):
    print(f"Request: {ctx['method']} {ctx['path']}")
    result = await next_middleware(ctx)
    print(f"Response: {result}")
    return result

client.router.use(logging_middleware)
```

## Development

To contribute to PyPolyCall development:

1. Clone the repository:
   ```
   git clone https://github.com/obinexuscomputing/pypolycall.git
   ```

2. Set up a development environment:
   ```
   cd pypolycall
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```
   pytest
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

Special thanks to Nnamdi Okpala and the OBINexusComputing team for creating the LibPolyCall library and architecture.