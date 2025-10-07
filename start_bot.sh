#!/bin/bash

# Script for safe HomeBox AI bot startup
# Automatically stops previous instances

echo "🤖 Starting HomeBox AI Bot..."

# Navigate to project directory
cd "$(dirname "$0")"

# Check if bot is already running
BOT_PID=$(ps aux | grep "python bot.py" | grep -v grep | awk '{print $2}')

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

# Activate virtual environment and start bot
echo "🚀 Starting new bot instance..."
source venv/bin/activate
python bot.py
