#!/bin/bash
set -e  # Exit on error

# =============================================================================
# Alejandro + WhisperLiveKit Installation Script for Vast.ai
# =============================================================================
# This script installs Alejandro and all dependencies on a Vast.ai instance
# Author: Charlie Mehlenbeck
# =============================================================================

echo "========================================"
echo "Alejandro + WLK Installation for Vast.ai"
echo "========================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${HOME}/projects"
GITHUB_USER="inventor2525"
PYTHON_VERSION="3.10"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_info "$1 is already installed"
        return 0
    else
        log_warn "$1 is not installed"
        return 1
    fi
}

# =============================================================================
# System Update and Basic Dependencies
# =============================================================================

log_info "Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

log_info "Installing essential build tools..."
sudo apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    vim \
    htop \
    tmux \
    software-properties-common \
    pkg-config \
    libssl-dev \
    libffi-dev \
    python3-dev

# =============================================================================
# Python Installation
# =============================================================================

log_info "Checking Python version..."
if ! check_command python3; then
    log_info "Installing Python ${PYTHON_VERSION}..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt-get update -y
    sudo apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-dev python${PYTHON_VERSION}-venv
fi

# Install pip
log_info "Installing pip..."
if ! check_command pip3; then
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
fi

# Upgrade pip
python3 -m pip install --upgrade pip setuptools wheel

# =============================================================================
# Audio Dependencies
# =============================================================================

log_info "Installing audio processing dependencies..."
sudo apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0

# =============================================================================
# Create Project Directory
# =============================================================================

log_info "Creating project directory at ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

# =============================================================================
# Clone Repositories
# =============================================================================

log_info "Cloning GitHub repositories..."

# Clone Alejandro
if [ ! -d "Alejandro" ]; then
    log_info "Cloning Alejandro..."
    git clone https://github.com/${GITHUB_USER}/Alejandro.git
else
    log_info "Alejandro already exists, pulling latest changes..."
    cd Alejandro && git pull && cd ..
fi

# Clone RequiredAI dependency
if [ ! -d "RequiredAI" ]; then
    log_info "Cloning RequiredAI..."
    git clone https://github.com/${GITHUB_USER}/RequiredAI.git
else
    log_info "RequiredAI already exists, pulling latest changes..."
    cd RequiredAI && git pull && cd ..
fi

# Clone assistant_merger dependency
if [ ! -d "assistant_merger" ]; then
    log_info "Cloning assistant_merger..."
    git clone https://github.com/${GITHUB_USER}/assistant_merger.git
else
    log_info "assistant_merger already exists, pulling latest changes..."
    cd assistant_merger && git pull && cd ..
fi

# Clone assistant_interaction dependency
if [ ! -d "assistant_interaction" ]; then
    log_info "Cloning assistant_interaction..."
    git clone https://github.com/${GITHUB_USER}/assistant_interaction.git
else
    log_info "assistant_interaction already exists, pulling latest changes..."
    cd assistant_interaction && git pull && cd ..
fi

# Clone WhisperLiveKit
if [ ! -d "WhisperLiveKit" ]; then
    log_info "Cloning WhisperLiveKit..."
    git clone https://github.com/QuentinFuxa/WhisperLiveKit.git
else
    log_info "WhisperLiveKit already exists, pulling latest changes..."
    cd WhisperLiveKit && git pull && cd ..
fi

# =============================================================================
# Python Virtual Environment (Optional but Recommended)
# =============================================================================

log_info "Setting up Python virtual environment..."
if [ ! -d "${INSTALL_DIR}/venv" ]; then
    python3 -m venv "${INSTALL_DIR}/venv"
    log_info "Virtual environment created at ${INSTALL_DIR}/venv"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment
source "${INSTALL_DIR}/venv/bin/activate"

# =============================================================================
# Install Python Dependencies
# =============================================================================

log_info "Installing Python dependencies..."

# Install core dependencies
pip install --upgrade pip

# Install dependencies in editable mode for development
log_info "Installing RequiredAI in editable mode..."
cd "${INSTALL_DIR}/RequiredAI"
pip install -e .

log_info "Installing assistant_merger in editable mode..."
cd "${INSTALL_DIR}/assistant_merger"
pip install -e .

log_info "Installing assistant_interaction in editable mode..."
cd "${INSTALL_DIR}/assistant_interaction"
pip install -e .

# Install Alejandro dependencies
log_info "Installing Alejandro dependencies..."
cd "${INSTALL_DIR}/Alejandro"
pip install flask flask-socketio groq dataclasses-json nltk websocket-client

# Install Alejandro in editable mode
log_info "Installing Alejandro in editable mode..."
pip install -e .

# Install WhisperLiveKit
log_info "Installing WhisperLiveKit..."
cd "${INSTALL_DIR}/WhisperLiveKit"
pip install -e .

# Additional dependencies that might be needed
log_info "Installing additional Python packages..."
pip install \
    numpy \
    torch \
    torchaudio \
    transformers \
    faster-whisper \
    python-dotenv \
    requests \
    pyyaml

# =============================================================================
# Download NLTK Data
# =============================================================================

log_info "Downloading NLTK data..."
python3 << EOF
import nltk
import ssl

# Handle SSL certificate issues
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required NLTK data
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
print("NLTK data downloaded successfully!")
EOF

# =============================================================================
# Environment Configuration
# =============================================================================

log_info "Setting up environment configuration..."

# Create .env file template
cat > "${INSTALL_DIR}/Alejandro/.env.template" << 'EOF'
# API Keys
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# WhisperLiveKit Configuration
WLK_HOST=localhost
WLK_PORT=8765

# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
EOF

# Create .env file if it doesn't exist
if [ ! -f "${INSTALL_DIR}/Alejandro/.env" ]; then
    cp "${INSTALL_DIR}/Alejandro/.env.template" "${INSTALL_DIR}/Alejandro/.env"
    log_warn "Created .env file. Please edit it and add your API keys!"
else
    log_info ".env file already exists"
fi

# =============================================================================
# Create Startup Scripts
# =============================================================================

log_info "Creating startup scripts..."

# Create activation helper script
cat > "${INSTALL_DIR}/activate.sh" << EOF
#!/bin/bash
source "${INSTALL_DIR}/venv/bin/activate"
cd "${INSTALL_DIR}/Alejandro"
export PYTHONPATH="${INSTALL_DIR}/Alejandro:\${PYTHONPATH}"
echo "Alejandro environment activated!"
echo "Current directory: \$(pwd)"
EOF
chmod +x "${INSTALL_DIR}/activate.sh"

# Create WhisperLiveKit startup script
cat > "${INSTALL_DIR}/start_wlk.sh" << EOF
#!/bin/bash
source "${INSTALL_DIR}/venv/bin/activate"
cd "${INSTALL_DIR}/WhisperLiveKit"

# Load environment variables
if [ -f "${INSTALL_DIR}/Alejandro/.env" ]; then
    export \$(cat "${INSTALL_DIR}/Alejandro/.env" | grep -v '^#' | xargs)
fi

# Start WhisperLiveKit server
python -m whisperlivekit.server --host \${WLK_HOST:-0.0.0.0} --port \${WLK_PORT:-8765}
EOF
chmod +x "${INSTALL_DIR}/start_wlk.sh"

# Create Alejandro startup script
cat > "${INSTALL_DIR}/start_alejandro.sh" << EOF
#!/bin/bash
source "${INSTALL_DIR}/venv/bin/activate"
cd "${INSTALL_DIR}/Alejandro"

# Load environment variables
if [ -f ".env" ]; then
    export \$(cat .env | grep -v '^#' | xargs)
fi

# Start Alejandro
python run.py
EOF
chmod +x "${INSTALL_DIR}/start_alejandro.sh"

# Create tmux session launcher
cat > "${INSTALL_DIR}/start_all.sh" << EOF
#!/bin/bash
# Start both WhisperLiveKit and Alejandro in tmux sessions

# Kill existing sessions if they exist
tmux kill-session -t wlk 2>/dev/null || true
tmux kill-session -t alejandro 2>/dev/null || true

# Start WhisperLiveKit in a tmux session
tmux new-session -d -s wlk "${INSTALL_DIR}/start_wlk.sh"
echo "WhisperLiveKit started in tmux session 'wlk'"
echo "Attach with: tmux attach -t wlk"

# Wait a bit for WLK to start
sleep 3

# Start Alejandro in a tmux session
tmux new-session -d -s alejandro "${INSTALL_DIR}/start_alejandro.sh"
echo "Alejandro started in tmux session 'alejandro'"
echo "Attach with: tmux attach -t alejandro"

echo ""
echo "Both services are running in tmux sessions!"
echo "To view sessions: tmux ls"
echo "To attach to WLK: tmux attach -t wlk"
echo "To attach to Alejandro: tmux attach -t alejandro"
echo "To detach from tmux: Ctrl+B then D"
EOF
chmod +x "${INSTALL_DIR}/start_all.sh"

# =============================================================================
# Port Forwarding Information
# =============================================================================

log_info "Creating port forwarding guide..."
cat > "${INSTALL_DIR}/PORT_FORWARDING.md" << 'EOF'
# Vast.ai Port Forwarding Guide

## Ports Used

- **5000**: Alejandro Flask web server
- **8765**: WhisperLiveKit WebSocket server

## Setting Up Port Forwarding on Vast.ai

1. Go to your Vast.ai instance page
2. Click "Open SSH/HTTP/HTTPS Ports"
3. Add port mappings:
   - `5000:5000` for Alejandro web interface
   - `8765:8765` for WhisperLiveKit WebSocket

## Accessing Your Services

After setting up port forwarding:

- Alejandro Web Interface: `http://<vast-instance-ip>:5000`
- WhisperLiveKit WebSocket: `ws://<vast-instance-ip>:8765`

## Security Note

For production use, consider:
- Using HTTPS/WSS with SSL certificates
- Setting up authentication
- Using a reverse proxy (nginx)
- Restricting IP access with firewall rules
EOF

# =============================================================================
# System Info
# =============================================================================

log_info "Gathering system information..."
cat > "${INSTALL_DIR}/SYSTEM_INFO.txt" << EOF
=== System Information ===
Hostname: $(hostname)
OS: $(lsb_release -d | cut -f2)
Kernel: $(uname -r)
Python: $(python3 --version)
Pip: $(pip3 --version)
Git: $(git --version)
FFmpeg: $(ffmpeg -version | head -n1)

=== GPU Information ===
$(nvidia-smi 2>/dev/null || echo "No NVIDIA GPU detected")

=== Disk Space ===
$(df -h ${INSTALL_DIR})

=== Installation Paths ===
Install Directory: ${INSTALL_DIR}
Virtual Environment: ${INSTALL_DIR}/venv
Alejandro: ${INSTALL_DIR}/Alejandro
WhisperLiveKit: ${INSTALL_DIR}/WhisperLiveKit

=== Environment ===
$(cat ${INSTALL_DIR}/Alejandro/.env.template)
EOF

# =============================================================================
# Installation Complete
# =============================================================================

echo ""
echo "========================================"
log_info "Installation Complete!"
echo "========================================"
echo ""
log_info "Installation directory: ${INSTALL_DIR}"
echo ""
echo "Next steps:"
echo "1. Edit your API keys: nano ${INSTALL_DIR}/Alejandro/.env"
echo "2. Activate environment: source ${INSTALL_DIR}/activate.sh"
echo "3. Start WhisperLiveKit: ${INSTALL_DIR}/start_wlk.sh"
echo "4. Start Alejandro: ${INSTALL_DIR}/start_alejandro.sh"
echo "   OR start both in tmux: ${INSTALL_DIR}/start_all.sh"
echo ""
log_warn "Don't forget to set up port forwarding on Vast.ai!"
log_info "See ${INSTALL_DIR}/PORT_FORWARDING.md for details"
echo ""
log_info "System info saved to: ${INSTALL_DIR}/SYSTEM_INFO.txt"
echo ""
echo "Happy coding! 🚀"
echo "========================================"

# Deactivate virtual environment
deactivate 2>/dev/null || true
