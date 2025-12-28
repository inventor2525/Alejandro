#!/bin/bash
set -e

echo "Installing system dependencies..."
apt-get update && apt-get install -y python3-pip git ffmpeg

echo "Installing Python dependencies..."
cd /home/user

# Clone and install RequiredAI
if [ ! -d "RequiredAI" ]; then
    echo "Cloning RequiredAI..."
    git clone https://github.com/inventor2525/RequiredAI.git
fi
cd RequiredAI && pip install -e . && cd ..

# Clone and install assistant_merger
if [ ! -d "assistant_merger" ]; then
    echo "Cloning assistant_merger..."
    git clone https://github.com/inventor2525/assistant_merger.git
fi
cd assistant_merger && pip install -e . && cd ..

# Clone and install assistant_interaction
if [ ! -d "assistant_interaction" ]; then
    echo "Cloning assistant_interaction..."
    git clone https://github.com/inventor2525/assistant_interaction.git
fi
cd assistant_interaction && pip install -e . && cd ..

# Install Alejandro in editable mode
echo "Installing Alejandro..."
cd Alejandro && pip install -e .

# Install WhisperLiveKit from PyPI
echo "Installing WhisperLiveKit..."
pip install whisperlivekit

echo "Installation complete!"
