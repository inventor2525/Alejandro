#!/bin/bash

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down Alejandro..."
    killall python 2>/dev/null || true
    echo "Shutdown complete"
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup INT TERM

# Kill any existing python processes
echo "Cleaning up existing processes..."
killall python 2>/dev/null || true
sleep 1

# Start RequiredAI server in background
echo "Starting RequiredAI server..."
python ~/Projects/Alejandro_dev/RequiredAI/examples/run_server.py > ~/required_ai.log 2>&1 &
REQUIRED_AI_PID=$!

# Wait for RequiredAI to initialize
echo "Waiting for RequiredAI to initialize..."
sleep 3

# Start Alejandro web app (this will stream to console)
echo ""
echo "Starting Alejandro web app..."
echo "Press Ctrl+C to shutdown all services"
echo ""

# Pipe to both file and console
python ~/Projects/Alejandro_dev/Alejandro/Alejandro/web/app.py 2>&1 | tee ~/alejandro.log

# If we reach here, the app exited
cleanup
