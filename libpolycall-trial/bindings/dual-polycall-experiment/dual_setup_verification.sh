#!/bin/bash

# LibPolyCall Dual Testing Setup Verification Script
# Verifies both Node.js and Python servers are properly configured for dual testing

set -e

echo "🔍 LibPolyCall Dual Testing Setup Verification"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Check counters
TOTAL_CHECKS=0
PASSED_CHECKS=0

check_status() {
    local description="$1"
    local status="$2"
    local message="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $description${NC}"
        [ -n "$message" ] && echo -e "   ${BLUE}ℹ️  $message${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  $description${NC}"
        [ -n "$message" ] && echo -e "   ${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $description${NC}"
        [ -n "$message" ] && echo -e "   ${RED}❌ $message${NC}"
    fi
}

# Check 1: Required files for Node.js server
echo -e "\n${BLUE}🟢 Checking Node.js Server Requirements${NC}"

if [ -f "server.js" ]; then
    check_status "Node.js server file exists" "PASS" "server.js found"
    
    # Check if server.js contains the right port
    if grep -q "8084" server.js; then
        check_status "Node.js server configured for port 8084" "PASS" "Port 8084 found in server.js"
    else
        check_status "Node.js server configured for port 8084" "WARN" "Port 8084 not explicitly found in server.js"
    fi
else
    check_status "Node.js server file exists" "FAIL" "server.js not found in current directory"
fi

# Check Node.js dependencies
if [ -f "package.json" ]; then
    check_status "Node.js package.json exists" "PASS" "package.json found"
else
    check_status "Node.js package.json exists" "WARN" "package.json not found - may not be in Node.js project root"
fi

# Check 2: Required files for Python server
echo -e "\n${PURPLE}🐍 Checking Python Server Requirements${NC}"

PYTHON_SERVER_FILES=(
    "pypolycall_dual_server.py"
    "examples/server.py"
    "pypolycall/examples/server.py"
    "server.py"
)

PYTHON_SERVER_FOUND=""
for file in "${PYTHON_SERVER_FILES[@]}"; do
    if [ -f "$file" ]; then
        PYTHON_SERVER_FOUND="$file"
        break
    fi
done

if [ -n "$PYTHON_SERVER_FOUND" ]; then
    check_status "Python server file exists" "PASS" "$PYTHON_SERVER_FOUND found"
    
    # Check if Python server is configured for correct port
    if grep -q "3001" "$PYTHON_SERVER_FOUND"; then
        check_status "Python server configured for port 3001" "PASS" "Port 3001 found in $PYTHON_SERVER_FOUND"
    else
        check_status "Python server configured for port 3001" "WARN" "Port 3001 not found in $PYTHON_SERVER_FOUND"
    fi
else
    check_status "Python server file exists" "FAIL" "No Python server file found"
fi

# Check PyPolyCall package structure
if [ -d "pypolycall" ]; then
    check_status "PyPolyCall package directory exists" "PASS" "pypolycall/ directory found"
    
    if [ -f "pypolycall/setup.py" ]; then
        check_status "PyPolyCall setup.py exists" "PASS" "setup.py found in pypolycall/"
    else
        check_status "PyPolyCall setup.py exists" "WARN" "setup.py not found in pypolycall/"
    fi
else
    check_status "PyPolyCall package directory exists" "WARN" "pypolycall/ directory not found"
fi

# Check 3: Test client files
echo -e "\n${BLUE}🧪 Checking Test Client Files${NC}"

if [ -f "dual_test_client.py" ]; then
    check_status "Dual test client exists" "PASS" "dual_test_client.py found"
else
    check_status "Dual test client exists" "WARN" "dual_test_client.py not found"
fi

if [ -f "dual_testing_interface.html" ]; then
    check_status "Dual testing HTML interface exists" "PASS" "dual_testing_interface.html found"
else
    check_status "Dual testing HTML interface exists" "WARN" "dual_testing_interface.html not found"
fi

# Check 4: Port availability
echo -e "\n${BLUE}🌐 Checking Port Availability${NC}"

# Check if Node.js port (8084) is available
if command -v netstat >/dev/null 2>&1; then
    if netstat -tuln 2>/dev/null | grep -q ":8084 "; then
        check_status "Port 8084 availability" "WARN" "Port 8084 is in use (Node.js may already be running)"
    else
        check_status "Port 8084 availability" "PASS" "Port 8084 is available"
    fi
else
    check_status "Port 8084 availability" "WARN" "netstat not available - cannot check port status"
fi

# Check if Python port (3001) is available
if command -v netstat >/dev/null 2>&1; then
    if netstat -tuln 2>/dev/null | grep -q ":3001 "; then
        check_status "Port 3001 availability" "WARN" "Port 3001 is in use (Python may already be running)"
    else
        check_status "Port 3001 availability" "PASS" "Port 3001 is available"
    fi
fi

# Check 5: Runtime requirements
echo -e "\n${BLUE}🔧 Checking Runtime Requirements${NC}"

# Check Node.js
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version)
    check_status "Node.js installed" "PASS" "Node.js $NODE_VERSION"
else
    check_status "Node.js installed" "FAIL" "Node.js not found in PATH"
fi

# Check Python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version)
    check_status "Python 3 installed" "PASS" "$PYTHON_VERSION"
else
    check_status "Python 3 installed" "FAIL" "Python 3 not found in PATH"
fi

# Check curl for testing
if command -v curl >/dev/null 2>&1; then
    check_status "curl available for testing" "PASS" "curl found"
else
    check_status "curl available for testing" "WARN" "curl not found - needed for server testing"
fi

# Check 6: Startup script
echo -e "\n${BLUE}🚀 Checking Startup Scripts${NC}"

if [ -f "dual_server_startup.sh" ]; then
    check_status "Dual server startup script exists" "PASS" "dual_server_startup.sh found"
    
    if [ -x "dual_server_startup.sh" ]; then
        check_status "Startup script is executable" "PASS" "Execute permissions verified"
    else
        check_status "Startup script is executable" "WARN" "Run: chmod +x dual_server_startup.sh"
    fi
else
    check_status "Dual server startup script exists" "WARN" "dual_server_startup.sh not found"
fi

# Summary and recommendations
echo -e "\n${BLUE}📋 Verification Summary${NC}"
echo "========================"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}🎉 All checks passed! ($PASSED_CHECKS/$TOTAL_CHECKS)${NC}"
    echo -e "${GREEN}✅ Dual testing environment is ready${NC}"
    echo ""
    echo -e "${BLUE}🚀 Ready to start dual testing:${NC}"
    echo "   1. Start both servers: ./dual_server_startup.sh start"
    echo "   2. Run tests: python3 dual_test_client.py"
    echo "   3. Open web interface: dual_testing_interface.html"
    
elif [ $PASSED_CHECKS -gt $((TOTAL_CHECKS * 3 / 4)) ]; then
    echo -e "${YELLOW}⚠️  Most checks passed ($PASSED_CHECKS/$TOTAL_CHECKS)${NC}"
    echo -e "${YELLOW}🔧 Address the warnings above for optimal testing${NC}"
    echo ""
    echo -e "${BLUE}🚀 You can proceed with testing:${NC}"
    echo "   1. Start servers: ./dual_server_startup.sh start"
    echo "   2. Monitor logs for any issues"
    
else
    echo -e "${RED}❌ Multiple checks failed ($PASSED_CHECKS/$TOTAL_CHECKS)${NC}"
    echo -e "${RED}🛠️  Setup required before dual testing${NC}"
fi

echo ""
echo -e "${BLUE}📊 Dual Testing Configuration:${NC}"
echo "   🟢 Node.js Server: Port 8084"
echo "   🐍 Python Server: Port 3001"
echo "   🧪 Test Client: dual_test_client.py"
echo "   🌐 Web Interface: dual_testing_interface.html"
echo "   🚀 Startup Script: dual_server_startup.sh"

echo ""
echo -e "${BLUE}🔧 Quick Setup Commands:${NC}"
echo "   # Make scripts executable"
echo "   chmod +x dual_server_startup.sh"
echo "   chmod +x dual_test_client.py"
echo ""
echo "   # Install Node.js dependencies (if needed)"
echo "   npm install"
echo ""
echo "   # Install PyPolyCall (if needed)"
echo "   cd pypolycall && pip install -e ."
echo ""
echo "   # Start dual testing"
echo "   ./dual_server_startup.sh start"

# Create quick setup script if needed
if [ $PASSED_CHECKS -lt $TOTAL_CHECKS ]; then
    echo ""
    echo -e "${YELLOW}💡 Creating quick setup script...${NC}"
    
    cat > quick_dual_setup.sh << 'EOF'
#!/bin/bash
# Quick Dual Testing Setup

echo "🔧 Quick Dual Testing Setup"
echo "=========================="

# Make scripts executable
chmod +x dual_server_startup.sh 2>/dev/null || echo "dual_server_startup.sh not found"
chmod +x dual_test_client.py 2>/dev/null || echo "dual_test_client.py not found"

# Install Node.js dependencies if package.json exists
if [ -f "package.json" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Install PyPolyCall if directory exists
if [ -d "pypolycall" ]; then
    echo "🐍 Installing PyPolyCall..."
    cd pypolycall
    pip install -e . 2>/dev/null || pip3 install -e . 2>/dev/null || echo "Failed to install PyPolyCall"
    cd ..
fi

echo "✅ Quick setup complete!"
echo "🚀 Run: ./dual_server_startup.sh start"
EOF
    
    chmod +x quick_dual_setup.sh
    echo -e "${GREEN}✅ Created quick_dual_setup.sh${NC}"
    echo "   Run: ./quick_dual_setup.sh"
fi
