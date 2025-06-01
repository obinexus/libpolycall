# PyPolyCall - Python Binding for LibPolyCall

## Overview

PyPolyCall is the official Python binding for LibPolyCall, providing strict port mapping and zero-trust security for Python applications.

## Port Mapping (Reserved)

```
Python Binding: 3001:8084 (RESERVED FOR PYTHON ONLY)
```

## Installation

```bash
pip install pypolycall
```

## Configuration

Manual configuration required (zero-trust principle):

```bash
# Copy configuration to system location
sudo cp python.polycallrc /opt/polycall/services/python/

# Verify strict port mapping
grep "port=3001:8084" /opt/polycall/services/python/python.polycallrc
```

## Quick Start

```python
from pypolycall import Router, State, PolyCallClient

# Create router
router = Router()

# Add routes
router.add_route('/books', {
    'GET': lambda ctx: {'success': True, 'data': []},
    'POST': lambda ctx: {'success': True, 'data': ctx.data}
})

# Start server (strict port: 8084)
pypolycall-server
```

## Zero-Trust Security

✅ **Strict port binding enforcement**  
✅ **No fallback ports allowed**  
✅ **Manual configuration required**  
✅ **Port overlap prevention**  
✅ **Configuration validation**  

## License

MIT
