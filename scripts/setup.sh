#!/bin/bash

# Hungry Agent - Setup Script for MacBook M3
# This script sets up the complete voice-based taco ordering system

set -e  # Exit on any error

echo "🚀 Setting up Hungry Agent - Voice-Based Taco Ordering System"
echo "================================================================"

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This setup script is designed for macOS (MacBook M3)"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Homebrew if not present
install_homebrew() {
    if ! command_exists brew; then
        echo "📦 Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ $(uname -m) == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo "✅ Homebrew already installed"
    fi
}

# Function to install system dependencies
install_system_deps() {
    echo "📦 Installing system dependencies..."
    
    # Core build tools and libraries
    brew install cmake pkg-config ffmpeg
    
    # Python 3.11 (as specified in requirements)
    brew install python@3.11
    
    # Node.js for dashboard and MCP servers
    brew install node
    
    # Process management
    brew install foreman
    
    # Development tools
    brew install just git
    
    echo "✅ System dependencies installed"
}

# Function to setup Python virtual environment
setup_python_env() {
    echo "🐍 Setting up Python virtual environment..."
    
    # Create virtual environment with Python 3.11
    python3.11 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
    
    echo "✅ Python environment setup complete"
}

# Function to clone and setup MCP servers
setup_mcp_servers() {
    echo "🔗 Setting up MCP servers..."
    
    # Create submodules directory
    mkdir -p submodules
    
    # Clone Uber Eats MCP server
    if [ ! -d "submodules/uber-eats-mcp-server" ]; then
        echo "📥 Cloning Uber Eats MCP server..."
        git clone https://github.com/ericzakariasson/uber-eats-mcp-server.git submodules/uber-eats-mcp-server
    fi
    
    # Clone DoorDash MCP server
    if [ ! -d "submodules/doordash-mcp-server" ]; then
        echo "📥 Cloning DoorDash MCP server..."
        git clone https://github.com/JordanDalton/DoorDash-MCP-Server.git submodules/doordash-mcp-server
    fi
    
    # Setup Uber Eats MCP server
    echo "🔧 Setting up Uber Eats MCP server..."
    cd submodules/uber-eats-mcp-server
    
    # Activate our virtual environment for Python dependencies
    source ../../venv/bin/activate
    pip install -r requirements.txt
    
    # Install Playwright browsers
    playwright install chromium
    
    cd ../..
    
    # Setup DoorDash MCP server
    echo "🔧 Setting up DoorDash MCP server..."
    cd submodules/doordash-mcp-server
    npm install
    npm run build
    cd ../..
    
    echo "✅ MCP servers setup complete"
}

# Function to build Whisper.cpp with Core ML
build_whisper() {
    echo "🎤 Building Whisper.cpp with Core ML support..."
    
    if [ ! -d "submodules/whisper.cpp" ]; then
        echo "📥 Cloning Whisper.cpp..."
        git clone https://github.com/ggerganov/whisper.cpp.git submodules/whisper.cpp
    fi
    
    cd submodules/whisper.cpp
    
    # Build with Core ML support for Apple Silicon
    echo "🔨 Building with Core ML support..."
    make clean
    WHISPER_COREML=1 make -j$(sysctl -n hw.ncpu)
    
    # Download tiny model for fast processing
    echo "📥 Downloading Whisper tiny model..."
    if [ ! -f "models/ggml-tiny.bin" ]; then
        bash ./models/download-ggml-model.sh tiny
    fi
    
    cd ../..
    
    echo "✅ Whisper.cpp built with Core ML support"
}

# Function to setup dashboard
setup_dashboard() {
    echo "📊 Setting up React dashboard..."
    
    cd dashboard
    
    # Install Node.js dependencies
    npm install
    
    # Build Tailwind CSS
    npx tailwindcss build -o src/index.css
    
    cd ..
    
    echo "✅ Dashboard setup complete"
}

# Function to create environment file
create_env_file() {
    echo "⚙️ Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "📝 Created .env file from template"
        echo ""
        echo "🔑 IMPORTANT: Please edit .env file and add your API keys:"
        echo "   - ANTHROPIC_API_KEY (required)"
        echo "   - UBER_EATS_EMAIL and UBER_EATS_PASSWORD"
        echo "   - DOORDASH_EMAIL and DOORDASH_PASSWORD"
        echo ""
    else
        echo "✅ .env file already exists"
    fi
}

# Function to create necessary directories
create_directories() {
    echo "📁 Creating necessary directories..."
    
    mkdir -p database
    mkdir -p logs
    
    echo "✅ Directories created"
}

# Function to verify installation
verify_installation() {
    echo "🔍 Verifying installation..."
    
    # Check Python environment
    if [ -f "venv/bin/activate" ]; then
        echo "✅ Python virtual environment: OK"
    else
        echo "❌ Python virtual environment: MISSING"
        return 1
    fi
    
    # Check MCP servers
    if [ -d "submodules/uber-eats-mcp-server" ] && [ -d "submodules/doordash-mcp-server" ]; then
        echo "✅ MCP servers: OK"
    else
        echo "❌ MCP servers: MISSING"
        return 1
    fi
    
    # Check Whisper.cpp
    if [ -f "submodules/whisper.cpp/main" ]; then
        echo "✅ Whisper.cpp: OK"
    else
        echo "❌ Whisper.cpp: MISSING"
        return 1
    fi
    
    # Check dashboard
    if [ -d "dashboard/node_modules" ]; then
        echo "✅ Dashboard: OK"
    else
        echo "❌ Dashboard: MISSING"
        return 1
    fi
    
    echo "✅ Installation verification complete"
}

# Main setup function
main() {
    echo "Starting setup process..."
    echo ""
    
    # Install Homebrew
    install_homebrew
    
    # Install system dependencies
    install_system_deps
    
    # Setup Python environment
    setup_python_env
    
    # Setup MCP servers
    setup_mcp_servers
    
    # Build Whisper.cpp
    build_whisper
    
    # Setup dashboard
    setup_dashboard
    
    # Create environment file
    create_env_file
    
    # Create directories
    create_directories
    
    # Verify installation
    verify_installation
    
    echo ""
    echo "🎉 Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your API keys"
    echo "2. Run 'source venv/bin/activate' to activate Python environment"
    echo "3. Run 'just dev' to start all services"
    echo "4. Open http://localhost:3000 for the dashboard"
    echo ""
    echo "For more commands, run 'just --list'"
}

# Run main function
main "$@"
