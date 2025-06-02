# libpolycall
A Program First Data-Oriented Program Interface Implementation

## Author
OBINexusComputing - Nnamdi Michael Okpala

## Overview

libpolycall is a polymorphic library that implements a program-first approach to interface design and business integration. It uses both direct protocol implementation and stateless HTTPS architecture to serve clients.

## Key Features

- Program-primary interface design 
- Stateless HTTPS communication
- Flexible client bindings
- Strong state management
- Network transport flexibility
- Open source architecture

## Why LibPolycall
### Program First vs Binding First

Traditional approaches:
- Focus on language-specific bindings
- Require separate implementations for each language
- Tight coupling between implementation and binding

libpolycall's approach:
- Programs drive the implementation
- Bindings are thin code mappings
- Implementation details remain with drivers
- Language agnostic core

## Architecture

libpolycall consists of:
- Core protocol implementation
- State machine management
- Network communication layer
- Checksum and integrity verification
- Driver system for hardware/platform specifics

### Drivers vs Bindings

**Drivers:**
- Contain implementation-specific details
- Handle hardware/platform interactions
- Maintain their own state
- Implement core protocols

**Bindings:**
- Map language constructs to libpolycall APIs
- No implementation details
- Pure interface translation
- Lightweight and stateless

## Building from Source

### Prerequisites
```bash
# Required packages
sudo apt-get install build-essential cmake libssl-dev make
```

### Build Steps
```bash
# Clone repository
git clone https://gitlab.com/obinexuscomputing.pkg/libpolycall.git
cd libpolycall

# Create build directory
mkdir build && cd build

# Configure and build
cmake ..
make

# Install
sudo make install
```

## Usage Examples

### Node.js
```javascript
const { PolyCallClient } = require('node-polycall');

const client = new PolyCallClient({
  host: 'localhost',
  port: 8080
});

client.on('connected', () => {
  console.log('Connected to libpolycall server');
});

await client.connect();
```

### Python
```python
import requests

# Make requests to libpolycall server
response = requests.get('https://libpolycall-server/api/endpoint')
data = response.json()
```

### Browser
```javascript
import { PolyCallClient } from '@obinexuscomputing/polycall-web';

const client = new PolyCallClient({
  websocket: true,
  endpoint: 'ws://localhost:8080'
});

client.on('state:changed', ({from, to}) => {
  console.log(`State transition: ${from} -> ${to}`);
});
```

## Benefits

- Program-first design enables clean separation of concerns
- Drivers handle implementation details independently
- Bindings remain thin and maintainable
- Platform/language agnostic core protocol
- Strong state management and integrity checks
- Secure data handling
- Scalable architecture

## License

MIT License. Copyright (c) OBINexusComputing.
Attribution required for business use.

## Contributing

Please read CONTRIBUTING.md for details on submitting pull requests.
