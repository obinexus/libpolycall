# 🔄 LibPolyCall Dual Testing Setup Guide

## Overview

This guide sets up **dual testing** for LibPolyCall, allowing you to run and test both **Node.js** and **Python** bindings simultaneously. This ensures compatibility and validates that both language bindings work correctly with the LibPolyCall core system.

## 🎯 Goal

- **Node.js Server**: Port 8084 (🟢 Node.js PolyCall)
- **Python Server**: Port 3001 (🐍 PyPolyCall)
- **Dual Testing**: Simultaneous testing of both servers
- **Zero-Trust**: Strict port binding and isolated execution

## 📋 Prerequisites

### Required Software
- **Node.js** (v14+): For Node.js PolyCall server
- **Python 3.8+**: For PyPolyCall server  
- **curl**: For server connectivity testing
- **Git**: For repository management

### Required Files
```
libpolycall-project/
├── server.js                    # Node.js server (port 8084)
├── pypolycall_dual_server.py   # Python server (port 3001)
├── dual_test_client.py         # Test client for both servers
├── dual_testing_interface.html # Web interface for testing
├── dual_server_startup.sh      # Startup script for both servers
└── dual_setup_verification.sh  # Verification script
```

## 🚀 Quick Start

### Step 1: Verify Setup
```bash
# Run verification script
./dual_setup_verification.sh

# If verification fails, run quick setup
./quick_dual_setup.sh
```

### Step 2: Start Dual Servers
```bash
# Start both servers automatically
./dual_server_startup.sh start

# Or use interactive menu
./dual_server_startup.sh menu
```

### Step 3: Test the Setup
```bash
# Run automated dual test
python3 dual_test_client.py

# Or open web interface
open dual_testing_interface.html
```

## 📁 Detailed Setup

### 1. Node.js Server Setup

The Node.js server (`server.js`) should be configured to run on **port 8084**:

```javascript
const PORT = 8084;
server.listen(PORT, () => {
    console.log(`🟢 Node.js PolyCall Server running on port ${PORT}`);
});
```

**Key Features:**
- Book management API (`/books`)
- CORS enabled for dual testing
- JSON response format
- Router-based request handling

### 2. Python Server Setup

The Python server (`pypolycall_dual_server.py`) runs on **port 3001**:

```python
PYTHON_PORT = 3001  # Python binding port

def main():
    server = PyPolyCallDualServer()
    server.start(PYTHON_PORT)
```

**Key Features:**
- Same book management API as Node.js
- Python-exclusive endpoints (`/python/books`)
- Server identification in responses
- Zero-trust port binding

### 3. Dual Testing Client

The test client (`dual_test_client.py`) tests both servers simultaneously:

```bash
python3 dual_test_client.py
```

**Test Coverage:**
- ✅ Server connectivity
- ✅ GET /books endpoint
- ✅ POST /books endpoint  
- ✅ Python-exclusive endpoints
- ✅ Cross-server comparison

### 4. Web Interface

Open `dual_testing_interface.html` in your browser for visual testing:

**Features:**
- Real-time server status
- Book management for both servers
- Dual testing controls
- Live test logs
- Server comparison tools

## 🔧 Server Management

### Starting Servers

```bash
# Start both servers
./dual_server_startup.sh start

# Start with status monitoring
./dual_server_startup.sh start && ./dual_server_startup.sh status
```

### Monitoring Servers

```bash
# Check server status
./dual_server_startup.sh status

# View live logs
./dual_server_startup.sh logs

# Run connectivity test
./dual_server_startup.sh test
```

### Stopping Servers

```bash
# Stop both servers gracefully
./dual_server_startup.sh stop

# Force stop if needed
killall node python3
```

## 🧪 Testing Scenarios

### Basic Dual Test
```bash
# Automated test of both servers
python3 dual_test_client.py
```

### Manual API Testing

**Node.js Server (Port 8084):**
```bash
# Test Node.js server
curl http://localhost:8084/books
curl -X POST http://localhost:8084/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Node.js Book","author":"Node Author"}'
```

**Python Server (Port 3001):**
```bash
# Test Python server
curl http://localhost:3001/books
curl -X POST http://localhost:3001/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Python Book","author":"Python Author"}'

# Test Python-exclusive endpoint
curl -X POST http://localhost:3001/python/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Python-Only Book","author":"PyPolyCall"}'
```

### Web Interface Testing

1. Open `dual_testing_interface.html` in browser
2. Click "🔍 Check All Servers"
3. Use "🧪 Run Dual Test" for comprehensive testing
4. Add books using the form
5. Test Python-exclusive features

## 📊 Port Configuration

| Service | Host Port | Container Port | Binding |
|---------|-----------|----------------|---------|
| Node.js | 8080 | 8084 | JavaScript |
| Python | 3001 | 3001 | Python |

**Zero-Trust Security:**
- ✅ Strict port binding enforcement
- ✅ No fallback ports allowed
- ✅ Isolated execution environments
- ✅ Configuration validation required

## 🔍 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
# Check which process is using the port
lsof -i :8084
lsof -i :3001

# Kill processes using the ports
./dual_server_startup.sh stop
```

**Python Import Errors:**
```bash
# Install PyPolyCall package
cd pypolycall
pip install -e .

# Or install dependencies manually
pip install -r requirements.txt
```

**Node.js Module Errors:**
```bash
# Install Node.js dependencies
npm install

# Or install specific modules
npm install express cors
```

### Debug Mode

**Enable detailed logging:**
```bash
# Start servers with debug output
DEBUG=1 ./dual_server_startup.sh start

# Monitor logs in real-time
tail -f logs/nodejs.log logs/python.log
```

**Check server health:**
```bash
# Quick connectivity test
curl -I http://localhost:8084/books
curl -I http://localhost:3001/books
```

## 📈 Advanced Testing

### Load Testing
```bash
# Simple load test using curl
for i in {1..10}; do
  curl -X POST http://localhost:8084/books \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"Load Test $i\",\"author\":\"Test\"}" &
done
wait
```

### Concurrent Testing
```python
# Use dual_test_client.py with threading
import threading

def test_server(server):
    # Run multiple tests simultaneously
    pass

# Run tests on both servers concurrently
threading.Thread(target=test_server, args=['nodejs']).start()
threading.Thread(target=test_server, args=['python']).start()
```

## 🛡️ Security Considerations

**Zero-Trust Implementation:**
- Each server binds to specific ports only
- No cross-port communication allowed
- Manual configuration required
- Strict validation of all requests

**Network Isolation:**
- Node.js: localhost:8084 only
- Python: localhost:3001 only  
- No shared state between servers
- Independent authentication if implemented

## 📝 Configuration Files

### Node.js Configuration
```javascript
// server.js
const config = {
    port: 8084,
    host: 'localhost',
    cors: true,
    binding: 'nodejs'
};
```

### Python Configuration
```python
# pypolycall_dual_server.py
PYTHON_PORT = 3001
PYTHON_HOST = 'localhost'
DUAL_TESTING = True
```

## 🎉 Success Indicators

Your dual testing setup is working correctly when:

- ✅ Both servers start without port conflicts
- ✅ `dual_test_client.py` passes all tests
- ✅ Web interface shows both servers as "Online"  
- ✅ Books can be created on both servers
- ✅ Python-exclusive endpoints work
- ✅ No errors in server logs

## 📚 API Reference

### Common Endpoints (Both Servers)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/books` | List all books |
| POST | `/books` | Create a new book |
| GET | `/status` | Server status |

### Python-Exclusive Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/python/books` | Python-only books |
| POST | `/python/books` | Create Python-only book |

### Response Format

**Success Response:**
```json
{
  "success": true,
  "data": {...},
  "server": "PyPolyCall-Python",
  "port": 3001,
  "timestamp": "2025-06-01T12:00:00.000Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "server": "PyPolyCall-Python",
  "port": 3001
}
```

---

## 🤝 Support

For issues with dual testing setup:

1. Run `./dual_setup_verification.sh` to identify problems
2. Check server logs in `./logs/` directory  
3. Verify port availability with `netstat -tuln | grep :8084`
4. Test individual servers before dual testing

**Happy Dual Testing! 🎉**