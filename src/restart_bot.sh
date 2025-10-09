#!/bin/bash
# Auto-generated restart script
echo "Restarting HomeBox AI Bot..."

# Wait a moment to allow the current bot to finish sending messages
echo "Waiting for bot to finish current operations..."
sleep 5

# Try to gracefully stop existing bot processes first
if [ -f "../bot.pid" ]; then
    PID=$(cat ../bot.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "Sending SIGTERM to bot process $PID"
        kill -TERM "$PID" 2>/dev/null || true
        sleep 5
        # If still running, force kill
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing bot process $PID"
            kill -KILL "$PID" 2>/dev/null || true
        fi
    fi
fi

# Kill any remaining bot processes
echo "Killing any remaining bot processes..."
pkill -f "python.*main.py" 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 2

# Start new bot instance
cd /home/kiroru/dev/homebox-ai-bot
source .venv/bin/activate
cd src
nohup python main.py > ../logs/bot.log 2>&1 &
echo $! > ../bot.pid

echo "Bot restarted successfully"
