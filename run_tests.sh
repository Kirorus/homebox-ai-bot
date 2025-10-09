#!/bin/bash

# Test runner script for HomeBox AI Bot

set -e

echo "🧪 Running HomeBox AI Bot Tests"
echo "================================"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Please activate it first:"
    echo "   source venv/bin/activate"
    exit 1
fi

# Install test dependencies if not already installed
echo "📦 Installing test dependencies..."
pip install -r requirements.txt

# Run tests with coverage
echo "🚀 Running tests..."
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report generated in htmlcov/index.html"

# Optional: Run specific test categories
if [ "$1" == "unit" ]; then
    echo "🔬 Running unit tests only..."
    pytest tests/unit/ -v -m unit
elif [ "$1" == "integration" ]; then
    echo "🔗 Running integration tests only..."
    pytest tests/integration/ -v -m integration
elif [ "$1" == "handlers" ]; then
    echo "🎯 Running handler tests only..."
    pytest tests/handlers/ -v
elif [ "$1" == "fast" ]; then
    echo "⚡ Running fast tests only..."
    pytest tests/ -v -m "not slow"
elif [ "$1" == "coverage" ]; then
    echo "📊 Generating detailed coverage report..."
    pytest tests/ --cov=src --cov-report=html --cov-report=xml
    echo "Coverage report: htmlcov/index.html"
fi
