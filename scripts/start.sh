#!/bin/bash

# Hungry Agent - Start Script
# Starts all services for the voice-based taco ordering system

set -e

echo "🚀 Starting Hungry Agent - Voice-Based Taco Ordering System"
echo "============================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   bash scripts/setup.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it:"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your API keys"
    exit 1
fi

# Activate virtual environment
echo "🐍 Activating Python virtual environment..."
source venv/bin/activate

# Check if required API keys are set
echo "🔑 Checking environment configuration..."
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not configured in .env file"
    echo "   The system will not work without this API key"
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is already in use"
        return 1
    fi
    return 0
}

# Check if required ports are available
echo "🔍 Checking port availability..."
PORTS=(8000 3000 5001 5002)
for port in "${PORTS[@]}"; do
    if ! check_port $port; then
        echo "❌ Port $port is in use. Please stop the service using this port."
        echo "   You can find the process with: lsof -i :$port"
        exit 1
    fi
done

# Function to start service with logging
start_service() {
    local name=$1
    local command=$2
    local log_file="logs/${name}.log"
    
    echo "🔄 Starting $name..."
    
    # Start service in background with logging
    nohup bash -c "$command" > "$log_file" 2>&1 &
    local pid=$!
    
    # Store PID for cleanup
    echo $pid > "logs/${name}.pid"
    
    # Wait a moment and check if service started successfully
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        echo "✅ $name started (PID: $pid)"
    else
        echo "❌ Failed to start $name. Check logs/$name.log for details"
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo "✅ $name is ready"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $name failed to start within timeout"
    return 1
}

# Start services in order
echo ""
echo "🚀 Starting services..."

# 1. Start orchestrator (main FastAPI server)
start_service "orchestrator" "uvicorn orchestrator.app:app --host 127.0.0.1 --port 8000 --reload"

# Wait for orchestrator to be ready
wait_for_service "orchestrator" "http://localhost:8000/health"

# 2. Start MCP servers
echo ""
echo "🔗 Starting MCP servers..."

# Note: MCP servers are started on-demand by the orchestrator via stdio transport
# They don't run as persistent HTTP services, so we don't start them here
echo "✅ MCP servers will be started on-demand by the orchestrator"

# 3. Start voice services (optional, can be started separately)
echo ""
echo "🎤 Starting voice services..."

# Check if Whisper.cpp is available
if [ -f "submodules/whisper.cpp/main" ]; then
    start_service "voice-services" "python -m orchestrator.voice_services --port 5001"
else
    echo "⚠️  Whisper.cpp not found. Voice services will not be available."
    echo "   Run 'just build-whisper' to build Whisper.cpp"
fi

# 4. Start dashboard
echo ""
echo "📊 Starting dashboard..."

if [ -d "dashboard/node_modules" ]; then
    start_service "dashboard" "cd dashboard && npm start"
    
    # Wait for dashboard to be ready
    wait_for_service "dashboard" "http://localhost:3000"
else
    echo "⚠️  Dashboard dependencies not found. Run setup first."
fi

# Display status
echo ""
echo "🎉 Hungry Agent is starting up!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API: http://localhost:8000"
echo "📋 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs are available in the logs/ directory:"
echo "   - logs/orchestrator.log"
echo "   - logs/voice-services.log"
echo "   - logs/dashboard.log"
echo ""
echo "🛑 To stop all services, run: bash scripts/stop.sh"
echo ""

# Monitor services
echo "🔍 Monitoring services (Ctrl+C to exit monitoring)..."
echo "   Services will continue running in the background"
echo ""

# Function to check service status
check_services() {
    local all_running=true
    
    for service in orchestrator voice-services dashboard; do
        local pid_file="logs/${service}.pid"
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if kill -0 $pid 2>/dev/null; then
                echo "✅ $service (PID: $pid)"
            else
                echo "❌ $service (stopped)"
                all_running=false
            fi
        else
            echo "❓ $service (no PID file)"
            all_running=false
        fi
    done
    
    echo "🔗 MCP servers: Started on-demand by orchestrator"
    
    if [ "$all_running" = true ]; then
        return 0
    else
        return 1
    fi
}

# Monitor loop
trap 'echo ""; echo "👋 Monitoring stopped. Services are still running."; exit 0' INT

while true; do
    clear
    echo "🔍 Service Status - $(date)"
    echo "================================"
    check_services
    echo ""
    echo "Press Ctrl+C to stop monitoring (services will keep running)"
    echo "Run 'bash scripts/stop.sh' to stop all services"
    sleep 5
done
