#!/bin/bash

# LibPolyCall Dual Server Startup Script
# Starts both Node.js and Python servers for dual testing

set -e

echo "🚀 LibPolyCall Dual Server Startup"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
NODEJS_PORT=8084
PYTHON_PORT=3001
LOG_DIR="./logs"
PIDS_FILE="./dual_servers.pids"

# Create logs directory
mkdir -p "$LOG_DIR"

# Function to check if port is available
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port is already in use (may be $service already running)${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Port $port is available${NC}"
        return 0
    fi
}

# Function to start Node.js server
start_nodejs_server() {
    echo -e "\n${BLUE}🟢 Starting Node.js PolyCall Server${NC}"
    echo "   Port: $NODEJS_PORT"
    echo "   Binding: Node.js"
    
    if [ ! -f "server.js" ]; then
        echo -e "${RED}❌ server.js not found in current directory${NC}"
        return 1
    fi
    
    # Start Node.js server in background
    node server.js > "$LOG_DIR/nodejs.log" 2>&1 &
    NODEJS_PID=$!
    
    echo "$NODEJS_PID" >> "$PIDS_FILE"
    echo -e "${GREEN}✅ Node.js server started (PID: $NODEJS_PID)${NC}"
    
    # Wait a moment and check if it's running
    sleep 2
    if kill -0 $NODEJS_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Node.js server is running on port $NODEJS_PORT${NC}"
    else
        echo -e "${RED}❌ Node.js server failed to start${NC}"
        return 1
    fi
}

# Function to start Python server
start_python_server() {
    echo -e "\n${PURPLE}🐍 Starting PyPolyCall Server${NC}"
    echo "   Port: $PYTHON_PORT"
    echo "   Binding: Python"
    
    # Check for Python server file
    PYTHON_SERVER=""
    if [ -f "pypolycall_dual_server.py" ]; then
        PYTHON_SERVER="pypolycall_dual_server.py"
    elif [ -f "examples/server.py" ]; then
        PYTHON_SERVER="examples/server.py"
    elif [ -f "pypolycall/examples/server.py" ]; then
        PYTHON_SERVER="pypolycall/examples/server.py"
    else
        echo -e "${RED}❌ Python server file not found${NC}"
        echo "   Looked for: pypolycall_dual_server.py, examples/server.py, pypolycall/examples/server.py"
        return 1
    fi
    
    echo "   Using: $PYTHON_SERVER"
    
    # Start Python server in background
    python3 "$PYTHON_SERVER" > "$LOG_DIR/python.log" 2>&1 &
    PYTHON_PID=$!
    
    echo "$PYTHON_PID" >> "$PIDS_FILE"
    echo -e "${GREEN}✅ Python server started (PID: $PYTHON_PID)${NC}"
    
    # Wait a moment and check if it's running
    sleep 2
    if kill -0 $PYTHON_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Python server is running on port $PYTHON_PORT${NC}"
    else
        echo -e "${RED}❌ Python server failed to start${NC}"
        return 1
    fi
}

# Function to test servers
test_servers() {
    echo -e "\n${BLUE}🧪 Testing Server Connections${NC}"
    
    # Test Node.js server
    echo -n "   Testing Node.js server... "
    if curl -s "http://localhost:$NODEJS_PORT/books" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
    
    # Test Python server
    echo -n "   Testing Python server... "
    if curl -s "http://localhost:$PYTHON_PORT/books" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
}

# Function to show status
show_status() {
    echo -e "\n${BLUE}📊 Dual Server Status${NC}"
    echo "===================="
    
    if [ -f "$PIDS_FILE" ]; then
        while read pid; do
            if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
                # Get process info
                process_info=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                echo -e "${GREEN}✅ PID $pid ($process_info) - Running${NC}"
            else
                echo -e "${RED}❌ PID $pid - Not running${NC}"
            fi
        done < "$PIDS_FILE"
    else
        echo -e "${YELLOW}⚠️  No PID file found${NC}"
    fi
    
    echo ""
    echo "🌐 Server URLs:"
    echo "   🟢 Node.js: http://localhost:$NODEJS_PORT"
    echo "   🐍 Python:  http://localhost:$PYTHON_PORT"
    
    echo ""
    echo "📝 Log Files:"
    echo "   🟢 Node.js: $LOG_DIR/nodejs.log"
    echo "   🐍 Python:  $LOG_DIR/python.log"
}

# Function to stop servers
stop_servers() {
    echo -e "\n${YELLOW}🛑 Stopping Dual Servers${NC}"
    
    if [ -f "$PIDS_FILE" ]; then
        while read pid; do
            if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
                echo "   Stopping PID $pid..."
                kill $pid
                
                # Wait for graceful shutdown
                for i in {1..5}; do
                    if ! kill -0 $pid 2>/dev/null; then
                        echo -e "   ${GREEN}✅ PID $pid stopped${NC}"
                        break
                    fi
                    sleep 1
                done
                
                # Force kill if still running
                if kill -0 $pid 2>/dev/null; then
                    echo "   Force killing PID $pid..."
                    kill -9 $pid
                fi
            fi
        done < "$PIDS_FILE"
        
        rm -f "$PIDS_FILE"
    else
        echo -e "${YELLOW}⚠️  No PID file found, trying to kill by port${NC}"
        
        # Kill by port
        lsof -ti:$NODEJS_PORT | xargs kill -9 2>/dev/null || true
        lsof -ti:$PYTHON_PORT | xargs kill -9 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Servers stopped${NC}"
}

# Function to show logs
show_logs() {
    echo -e "\n${BLUE}📝 Server Logs${NC}"
    echo "============="
    
    if [ -f "$LOG_DIR/nodejs.log" ]; then
        echo -e "\n${GREEN}🟢 Node.js Log (last 10 lines):${NC}"
        tail -10 "$LOG_DIR/nodejs.log"
    fi
    
    if [ -f "$LOG_DIR/python.log" ]; then
        echo -e "\n${PURPLE}🐍 Python Log (last 10 lines):${NC}"
        tail -10 "$LOG_DIR/python.log"
    fi
}

# Function to run dual test
run_dual_test() {
    echo -e "\n${BLUE}🧪 Running Dual Server Test${NC}"
    
    if [ -f "dual_test_client.py" ]; then
        python3 dual_test_client.py
    else
        echo -e "${YELLOW}⚠️  dual_test_client.py not found, running basic test${NC}"
        test_servers
    fi
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}LibPolyCall Dual Server Management${NC}"
    echo "=================================="
    echo "1. Start dual servers"
    echo "2. Stop servers"  
    echo "3. Show status"
    echo "4. Show logs"
    echo "5. Run dual test"
    echo "6. Restart servers"
    echo "7. Exit"
    echo ""
}

# Main execution
case "${1:-menu}" in
    "start")
        echo "🚀 Starting dual servers automatically..."
        
        # Clean up any existing PID file
        rm -f "$PIDS_FILE"
        
        # Check ports
        echo "🔍 Checking port availability..."
        check_port $NODEJS_PORT "Node.js"
        check_port $PYTHON_PORT "Python"
        
        # Start servers
        if start_nodejs_server && start_python_server; then
            echo -e "\n${GREEN}🎉 Dual servers started successfully!${NC}"
            test_servers
            show_status
            
            echo -e "\n${BLUE}💡 Usage:${NC}"
            echo "   • Test: ./dual_server_startup.sh test"
            echo "   • Status: ./dual_server_startup.sh status"  
            echo "   • Stop: ./dual_server_startup.sh stop"
            echo "   • Logs: ./dual_server_startup.sh logs"
        else
            echo -e "\n${RED}❌ Failed to start one or more servers${NC}"
            stop_servers
            exit 1
        fi
        ;;
        
    "stop")
        stop_servers
        ;;
        
    "status")
        show_status
        ;;
        
    "logs")
        show_logs
        ;;
        
    "test")
        run_dual_test
        ;;
        
    "restart")
        stop_servers
        sleep 2
        exec "$0" start
        ;;
        
    "menu")
        while true; do
            show_menu
            read -p "Choose option [1-7]: " choice
            
            case $choice in
                1) exec "$0" start ;;
                2) stop_servers ;;
                3) show_status ;;
                4) show_logs ;;
                5) run_dual_test ;;
                6) exec "$0" restart ;;
                7) echo "Goodbye!"; exit 0 ;;
                *) echo -e "${RED}Invalid option${NC}" ;;
            esac
            
            echo ""
            read -p "Press Enter to continue..."
        done
        ;;
        
    *)
        echo "Usage: $0 {start|stop|status|logs|test|restart|menu}"
        echo ""
        echo "Commands:"
        echo "  start    - Start both servers"
        echo "  stop     - Stop both servers"
        echo "  status   - Show server status"
        echo "  logs     - Show server logs"
        echo "  test     - Run dual server test"
        echo "  restart  - Restart both servers"
        echo "  menu     - Interactive menu"
        ;;
esac
