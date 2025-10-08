#!/bin/bash

# Script for safe HomeBox AI bot startup
# Automatically stops previous instances

echo "🤖 Starting HomeBox AI Bot..."

# Navigate to project directory
cd "$(dirname "$0")"

# Check if bot is already running
BOT_PID=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}')

if [ ! -z "$BOT_PID" ]; then
    echo "⚠️  Found running bot instance (PID: $BOT_PID)"
    echo "🛑 Stopping previous instance..."
    kill $BOT_PID
    sleep 2
    
    # Check if process is actually stopped
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "🔨 Forcefully terminating process..."
        kill -9 $BOT_PID
        sleep 1
    fi
    
    echo "✅ Previous instance stopped"
fi

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
    echo "📦 Virtual environment not found. Creating new one..."
    python3 -m venv .venv
    echo "📥 Installing dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Virtual environment created and dependencies installed"
fi

# Activate virtual environment and start bot
echo "🚀 Starting new bot instance..."
source .venv/bin/activate
cd src && python main.py
