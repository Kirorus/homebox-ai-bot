#!/bin/bash

# Script for local Docker image building

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions for message output
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default parameters
IMAGE_NAME="homebox-ai-bot"
TAG="latest"
BUILD_ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        --no-cache)
            BUILD_ARGS="$BUILD_ARGS --no-cache"
            shift
            ;;
        --pull)
            BUILD_ARGS="$BUILD_ARGS --pull"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -n, --name NAME     Image name (default: homebox-ai-bot)"
            echo "  -t, --tag TAG       Image tag (default: latest)"
            echo "  --no-cache          Build without using cache"
            echo "  --pull              Update base image"
            echo "  -h, --help          Show this help"
            exit 0
            ;;
        *)
            error "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

log "Starting Docker image build..."
log "Image name: $IMAGE_NAME"
log "Tag: $TAG"

# Check for Dockerfile presence
if [ ! -f "Dockerfile" ]; then
    error "Dockerfile not found in current directory"
    exit 1
fi

# Check for requirements.txt presence
if [ ! -f "requirements.txt" ]; then
    warn "requirements.txt not found"
fi

# Build image
log "Building..."
if docker build $BUILD_ARGS -t "$IMAGE_NAME:$TAG" .; then
    log "Image successfully built: $IMAGE_NAME:$TAG"
    
    # Show image information
    log "Image information:"
    docker images "$IMAGE_NAME:$TAG"
    
    # Suggest running container
    echo ""
    log "To run use:"
    echo "  docker run -d --name homebox-ai-bot --env-file .env $IMAGE_NAME:$TAG"
    echo ""
    log "Or use docker-compose:"
    echo "  docker-compose up -d"
    
else
    error "Error building image"
    exit 1
fi
