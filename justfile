# Hungry Agent - Voice-Based Taco Ordering System
# Development shortcuts using just (brew install just)

# Default recipe - show available commands
default:
    @just --list

# Setup the development environment
setup:
    @echo "🚀 Setting up Hungry Agent development environment..."
    brew install cmake pkg-config ffmpeg python@3.11 node foreman just
    python3.11 -m venv venv
    @echo "✅ Virtual environment created. Run 'source venv/bin/activate' to activate."
    @echo "📝 Copy .env.example to .env and add your API keys"
    @echo "🔧 Run 'just install' after activating venv"

# Install Python dependencies
install:
    @echo "📦 Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    @echo "📦 Installing Node.js dependencies for dashboard..."
    cd dashboard && npm install
    @echo "✅ Dependencies installed"

# Clone and setup MCP server submodules
clone-mcp:
    @echo "📥 Cloning MCP server repositories..."
    mkdir -p submodules
    git clone https://github.com/ericzakariasson/uber-eats-mcp-server.git submodules/uber-eats-mcp-server
    git clone https://github.com/JordanDalton/DoorDash-MCP-Server.git submodules/doordash-mcp-server
    @echo "📦 Installing MCP server dependencies..."
    cd submodules/uber-eats-mcp-server && pip install -r requirements.txt && playwright install
    cd submodules/doordash-mcp-server && npm install && npm run build
    @echo "✅ MCP servers ready"

# Build Whisper.cpp with Core ML support
build-whisper:
    @echo "🔨 Building Whisper.cpp with Core ML support..."
    git clone https://github.com/ggerganov/whisper.cpp.git submodules/whisper.cpp
    cd submodules/whisper.cpp && make coreml
    @echo "✅ Whisper.cpp built with Core ML support"

# Start all services in development mode
dev:
    @echo "🚀 Starting all services..."
    foreman start -f Procfile

# Start only the orchestrator for testing
dev-orch:
    @echo "🎯 Starting orchestrator only..."
    uvicorn orchestrator.app:app --host 127.0.0.1 --port 8000 --reload

# Start only the dashboard
dev-dash:
    @echo "📊 Starting dashboard only..."
    cd dashboard && npm run dev

# Test the voice pipeline
test-voice:
    @echo "🎤 Testing voice pipeline..."
    python -m orchestrator.test_voice

# Test MCP server connections
test-mcp:
    @echo "🔗 Testing MCP server connections..."
    python -m orchestrator.test_mcp

# Clean up build artifacts and logs
clean:
    @echo "🧹 Cleaning up..."
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    rm -rf .pytest_cache
    rm -rf logs/*.log
    @echo "✅ Cleanup complete"

# Show system status
status:
    @echo "📊 System Status:"
    @echo "Python: $(python --version)"
    @echo "Node: $(node --version)"
    @echo "Foreman: $(foreman --version)"
    @echo "Virtual env: $VIRTUAL_ENV"
    @echo "Processes running:"
    @ps aux | grep -E "(uvicorn|node.*index|python.*server)" | grep -v grep || echo "No services running"

# Quick health check
health:
    @echo "🏥 Health check..."
    curl -s http://localhost:8000/health || echo "Orchestrator not running"
    curl -s http://localhost:3000 || echo "Dashboard not running"
    curl -s http://localhost:7001/health || echo "Uber MCP not running"
    curl -s http://localhost:7002/health || echo "DoorDash MCP not running"

# View logs
logs:
    @echo "📋 Recent logs:"
    tail -f logs/orchestrator.log

# Full setup from scratch
bootstrap: setup install clone-mcp build-whisper
    @echo "🎉 Bootstrap complete! Copy .env.example to .env and add your API keys"
    @echo "🚀 Then run 'just dev' to start all services"
