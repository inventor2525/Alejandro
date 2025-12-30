#!/bin/bash
set -e

echo "Installing system dependencies..."
apt-get update && apt-get install -y python3-pip git ffmpeg

echo "Setting up project directory..."
mkdir -p ~/Projects/Alejandro_dev
cd ~/Projects/Alejandro_dev

echo "Cloning repositories..."
git clone https://github.com/inventor2525/assistant_merger.git
git clone https://github.com/inventor2525/assistant_interaction.git
git clone https://github.com/inventor2525/RequiredAI.git
git clone https://github.com/inventor2525/Alejandro.git

echo "Installing assistant_merger..."
cd assistant_merger && pip install -e ./ && cd ~/Projects/Alejandro_dev

echo "Installing assistant_interaction..."
cd assistant_interaction && pip install -e ./ && cd ~/Projects/Alejandro_dev

echo "Installing RequiredAI..."
cd RequiredAI && pip install -e ./ && cd ~/Projects/Alejandro_dev

echo "Installing Alejandro..."
cd Alejandro && pip install -e ./ && cd ~/Projects/Alejandro_dev

echo "Installing WhisperLiveKit..."
pip install whisperlivekit

echo "Installation complete!"