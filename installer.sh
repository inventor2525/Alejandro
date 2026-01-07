#!/bin/bash
set -e

# Get ngrok token from parameter or prompt
NGROK_TOKEN="$1"
if [ -z "$NGROK_TOKEN" ]; then
    echo ""
    echo "======================================================================"
    echo "ngrok authentication token required"
    echo "You can pass it as a parameter: bash installer.sh YOUR_TOKEN"
    echo "Or enter it now:"
    echo "======================================================================"
    read -p "Enter ngrok auth token: " NGROK_TOKEN
fi

mkdir -p ~/Projects/Alejandro_dev
cd ~/Projects/Alejandro_dev

git clone https://github.com/inventor2525/assistant_merger.git
git clone https://github.com/inventor2525/assistant_interaction.git
git clone https://github.com/inventor2525/RequiredAI.git
git clone https://github.com/inventor2525/Alejandro.git

cd assistant_merger
pip install -e ./
cd ~/Projects/Alejandro_dev

cd assistant_interaction
pip install -e ./
cd ~/Projects/Alejandro_dev

cd RequiredAI
pip install -e ./
cd ~/Projects/Alejandro_dev

cd Alejandro
pip install -e ./
pip install whisperlivekit
cd ~/Projects/Alejandro_dev

# Install ngrok
echo ""
echo "Installing ngrok..."
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list \
  && sudo apt update \
  && sudo apt install -y ngrok

# Configure ngrok
echo ""
echo "Configuring ngrok..."
ngrok config add-authtoken "$NGROK_TOKEN"

# Start ngrok tunnel
echo ""
echo "Starting ngrok tunnel..."
ngrok http http://localhost:5000 > ~/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to initialize
sleep 2

# Extract ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)

echo ""
echo "======================================================================"
echo "Installation complete!"
echo "======================================================================"
echo ""
echo ""
echo ""
echo "**********************************************************************"
echo "**********************************************************************"
echo "**********************************************************************"
echo ""
echo "                    Alejandro Web Interface URL:"
echo ""
echo "  $NGROK_URL"
echo ""
echo "**********************************************************************"
echo "**********************************************************************"
echo "**********************************************************************"
echo ""
echo ""
echo "To start Alejandro, run:"
echo "  cd ~/Projects/Alejandro_dev/Alejandro"
echo "  ./run.sh"
echo ""
