#!/bin/bash

# Hungry Agent - Stop Script
# Stops all services for the voice-based taco ordering system

echo "🛑 Stopping Hungry Agent - Voice-Based Taco Ordering System"
echo "============================================================"

# Function to stop service by PID file
stop_service() {
    local name=$1
    local pid_file="logs/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if kill -0 $pid 2>/dev/null; then
            echo "🔄 Stopping $name (PID: $pid)..."
            
            # Try graceful shutdown first
            kill $pid
            
            # Wait up to 10 seconds for graceful shutdown
            local count=0
            while kill -0 $pid 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                echo "   Force killing $name..."
                kill -9 $pid
            fi
            
            echo "✅ $name stopped"
        else
            echo "⚠️  $name was not running"
        fi
        
        # Remove PID file
        rm -f "$pid_file"
    else
        echo "❓ No PID file found for $name"
    fi
}

# Function to stop services by port
stop_by_port() {
    local port=$1
    local service_name=$2
    
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "🔄 Stopping $service_name on port $port..."
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        
        # Wait a moment
        sleep 2
        
        # Force kill if still running
        local remaining_pids=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$remaining_pids" ]; then
            echo "   Force killing processes on port $port..."
            echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
        fi
        
        echo "✅ $service_name stopped"
    else
        echo "❓ No processes found on port $port for $service_name"
    fi
}

# Stop services by PID files first
echo "🔄 Stopping services by PID files..."
stop_service "orchestrator"
stop_service "voice-services"
stop_service "dashboard"

echo ""
echo "🔄 Checking for remaining processes on known ports..."

# Stop any remaining processes on known ports
stop_by_port 8000 "Orchestrator"
stop_by_port 3000 "Dashboard"
stop_by_port 5001 "Voice Services"
stop_by_port 5002 "TTS Service"

# Clean up any remaining Python processes related to our project
echo ""
echo "🧹 Cleaning up remaining processes..."

# Find and kill any remaining uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn.*orchestrator" 2>/dev/null || true)
if [ -n "$UVICORN_PIDS" ]; then
    echo "🔄 Stopping remaining uvicorn processes..."
    echo "$UVICORN_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    echo "$UVICORN_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Find and kill any remaining Node.js processes for our dashboard
NODE_PIDS=$(pgrep -f "node.*react-scripts" 2>/dev/null || true)
if [ -n "$NODE_PIDS" ]; then
    echo "🔄 Stopping remaining Node.js processes..."
    echo "$NODE_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    echo "$NODE_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Find and kill any remaining browser automation processes
BROWSER_PIDS=$(pgrep -f "python.*server.py" 2>/dev/null || true)
if [ -n "$BROWSER_PIDS" ]; then
    echo "🔄 Stopping remaining MCP server processes..."
    echo "$BROWSER_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 3
    echo "$BROWSER_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Find and kill any remaining Chrome browser processes started by browser-use
CHROME_PIDS=$(pgrep -f "chrome.*browseruse" 2>/dev/null || true)
if [ -n "$CHROME_PIDS" ]; then
    echo "🔄 Stopping browser automation Chrome processes..."
    echo "$CHROME_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    echo "$CHROME_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Clean up PID files
echo ""
echo "🧹 Cleaning up PID files..."
rm -f logs/*.pid

# Verify all services are stopped
echo ""
echo "🔍 Verifying services are stopped..."

PORTS=(8000 3000 5001 5002)
ALL_STOPPED=true

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is still in use"
        ALL_STOPPED=false
    else
        echo "✅ Port $port is free"
    fi
done

echo ""
if [ "$ALL_STOPPED" = true ]; then
    echo "🎉 All Hungry Agent services have been stopped successfully!"
else
    echo "⚠️  Some services may still be running. You can check with:"
    echo "   lsof -i :8000  # Orchestrator"
    echo "   lsof -i :3000  # Dashboard"
    echo "   lsof -i :5001  # Voice Services"
    echo "   lsof -i :5002  # TTS Service"
    echo ""
    echo "To force kill any remaining processes:"
    echo "   sudo lsof -ti:PORT | xargs kill -9"
fi

echo ""
echo "📝 Logs are preserved in the logs/ directory for debugging"
echo "🚀 To start services again, run: bash scripts/start.sh"
