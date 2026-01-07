#!/bin/bash

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down Alejandro..."
    killall python 2>/dev/null || true
    killall ngrok 2>/dev/null || true
    echo "Shutdown complete"
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup INT TERM

# Kill any existing python processes
echo "Cleaning up existing processes..."
killall python 2>/dev/null || true
killall ngrok 2>/dev/null || true
sleep 1

# Start RequiredAI server in background
echo "Starting RequiredAI server..."
python ~/Projects/Alejandro_dev/RequiredAI/examples/run_server.py > ~/required_ai.log 2>&1 &
REQUIRED_AI_PID=$!

# Wait for RequiredAI to initialize
echo "Waiting for RequiredAI to initialize..."
sleep 3

# Start ngrok in background
echo "Starting ngrok tunnel..."
ngrok http http://localhost:5000 > ~/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to initialize
sleep 2

# Extract ngrok URL
echo "Fetching ngrok URL..."
sleep 1
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)

# Start Alejandro web app (this will stream to console)
echo ""
echo "**********************************************************************"
echo "**********************************************************************"
echo "**********************************************************************"
echo ""
echo "                    Alejandro Web Interface"
echo ""
echo "  Public URL: $NGROK_URL"
echo ""
echo "**********************************************************************"
echo "**********************************************************************"
echo "**********************************************************************"
echo ""
echo "Starting Alejandro web app..."
echo "Press Ctrl+C to shutdown all services"
echo ""

# Pipe to both file and console
python ~/Projects/Alejandro_dev/Alejandro/Alejandro/web/app.py 2>&1 | tee ~/alejandro.log

# If we reach here, the app exited
cleanup
