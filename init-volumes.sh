#!/bin/bash

# Script to initialize directories for Docker volumes with correct permissions

echo "🔧 Initializing directories for Docker volumes..."

# Create directories if they don't exist
mkdir -p data logs temp

# Set proper permissions (readable/writable by owner and group)
chmod 755 data logs temp

# Try to change ownership to UID 1000 (if we have permissions)
if [ -w data ] && [ -w logs ] && [ -w temp ]; then
    echo "✅ All directories are writable"
    
    # If we can write, try to change ownership
    if command -v chown >/dev/null 2>&1; then
        echo "🔐 Attempting to change ownership to UID 1000..."
        # This might fail if we don't have sudo, but that's OK
        chown -R 1000:1000 data logs temp 2>/dev/null || echo "⚠️  Could not change ownership (run with sudo if needed)"
    fi
else
    echo "❌ Some directories are not writable"
    echo "Current permissions:"
    ls -la data logs temp
    exit 1
fi

echo "📁 Directory structure:"
ls -la data logs temp

echo "✅ Directory initialization completed"
echo ""
echo "🚀 Now you can run:"
echo "   docker-compose up -d"
