#!/bin/bash

# Script to stop HomeBox AI bot

echo "🛑 Stopping HomeBox AI Bot..."

# Find and stop all bot instances
BOT_PIDS=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}')

if [ -z "$BOT_PIDS" ]; then
    echo "ℹ️  Bot is not running"
    exit 0
fi

echo "🔍 Found bot instances: $BOT_PIDS"

for PID in $BOT_PIDS; do
    echo "🛑 Stopping process $PID..."
    kill $PID
    sleep 2
    
    # Check if process is actually stopped
    if ps -p $PID > /dev/null 2>&1; then
        echo "🔨 Forcefully terminating process $PID..."
        kill -9 $PID
    fi
done

echo "✅ All bot instances stopped"
