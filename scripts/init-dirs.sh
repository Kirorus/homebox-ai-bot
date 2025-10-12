#!/bin/bash

# Script to initialize directories for Docker volumes

echo "🔧 Initializing directories for Docker volumes..."

# Create directories if they don't exist
mkdir -p data logs temp

# Set proper permissions
chmod 755 data logs temp

# Check if directories are writable
if [ -w data ] && [ -w logs ] && [ -w temp ]; then
    echo "✅ All directories are writable"
else
    echo "❌ Some directories are not writable"
    echo "Current permissions:"
    ls -la data logs temp
    exit 1
fi

echo "📁 Directory structure:"
ls -la

echo "✅ Directory initialization completed"
