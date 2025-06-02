# Banking Api - LibPolyCall Example

## Description

Secure banking transaction processing

## Features

- Zero-trust authentication
- Transaction validation
- Real-time processing

## API Endpoints

- `/accounts`
- `/transactions`
- `/transfers`
- `/balances`

## Quick Start

1. **Install Dependencies**:
   ```bash
   # For Node.js
   npm install
   
   # For Python
   pip install -r requirements.txt
   ```

2. **Configure LibPolyCall**:
   ```bash
   # Ensure main config.Polycallfile includes:
   server node 3000:433
   ```

3. **Start Service**:
   ```bash
   # For Node.js
   npm start
   
   # For Python
   python src/server.py
   ```

4. **Test Service**:
   ```bash
   curl http://localhost:3000/health
   ```

## Configuration

LibPolyCall configuration is located in `config/.polycallrc`:

- **Port Mapping**: `3000:433`
- **Binding Type**: `node-polycall`
- **Service Name**: `banking-api`

## Architecture

This example demonstrates:

1. **LibPolyCall Integration**: Proper binding initialization and state management
2. **Zero-Trust Security**: Authentication and authorization implementation
3. **Production Patterns**: Error handling, logging, and monitoring
4. **Concrete Use Case**: Real-world business logic implementation

## Testing

```bash
cd tests/
# Run binding-specific tests
```

## Support

For issues specific to this example:
1. Check the configuration in `config/.polycallrc`
2. Verify LibPolyCall core is running
3. Review logs for binding errors
4. Consult main node-polycall documentation