"""
Process management utilities for bot restart functionality
"""
import os
import sys
import signal
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages bot process lifecycle"""
    
    def __init__(self):
        self.pid_file = "bot.pid"
        self.restart_script = "start_bot.sh"
    
    def get_current_pid(self) -> Optional[int]:
        """Get current bot process PID"""
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    return pid
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Could not read PID file: {e}")
        return None
    
    def is_process_running(self, pid: int) -> bool:
        """Check if process with given PID is running"""
        try:
            os.kill(pid, 0)  # Send signal 0 to check if process exists
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def restart_bot(self) -> bool:
        """
        Restart the bot process
        Returns True if restart was initiated successfully
        """
        try:
            logger.info("Initiating bot restart...")
            
            # Get current PID
            current_pid = self.get_current_pid()
            
            # Create restart script content
            restart_script_content = f"""#!/bin/bash
# Auto-generated restart script
echo "Restarting HomeBox AI Bot..."

# Kill existing bot processes
pkill -f "python.*main.py" 2>/dev/null || true

# Wait a moment
sleep 2

# Start new bot instance
cd {os.getcwd()}
source .venv/bin/activate
cd src
# Ensure logs directory exists and write logs and pid at project root
mkdir -p ../logs
nohup python main.py > ../logs/bot.log 2>&1 &
echo $! > ../bot.pid

echo "Bot restarted successfully"
"""
            
            # Write restart script
            with open("restart_bot.sh", "w") as f:
                f.write(restart_script_content)
            
            # Make script executable
            os.chmod("restart_bot.sh", 0o755)
            
            # Execute restart script in background
            subprocess.Popen(
                ["bash", "restart_bot.sh"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.getcwd()
            )
            
            logger.info("Bot restart script executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart bot: {e}")
            return False
    
    def graceful_shutdown(self) -> bool:
        """
        Gracefully shutdown the bot
        Returns True if shutdown was successful
        """
        try:
            logger.info("Initiating graceful shutdown...")
            
            # Send SIGTERM to current process
            os.kill(os.getpid(), signal.SIGTERM)
            return True
            
        except Exception as e:
            logger.error(f"Failed to shutdown gracefully: {e}")
            return False
