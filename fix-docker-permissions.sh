#!/bin/bash
# Script to fix Docker permissions for homebox-ai-bot

echo "Fixing Docker permissions for homebox-ai-bot..."

# Get current user UID and GID
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

echo "Current user UID: $CURRENT_UID, GID: $CURRENT_GID"

# Stop existing containers
echo "Stopping existing containers..."
sudo docker compose down

# Fix permissions on host directories
echo "Fixing permissions on host directories..."
sudo chown -R $CURRENT_UID:$CURRENT_GID logs data temp
sudo chmod -R 755 logs data temp
sudo chmod 644 logs/bot.log 2>/dev/null || true

# Build new image with correct user
echo "Building new Docker image..."
sudo docker build --no-cache -t kirorus/homebox-ai-bot:latest .

# Start containers
echo "Starting containers..."
sudo docker compose up -d

echo "Done! Check logs with: sudo docker compose logs -f"
