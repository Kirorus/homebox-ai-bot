#!/bin/bash

# Script for bot deployment using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Default parameters
COMPOSE_FILE="docker-compose.yaml"
ENV_FILE=".env"
ACTION="up"
SERVICES=""
DETACHED=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -s|--service)
            SERVICES="$2"
            shift 2
            ;;
        --prod)
            warn "Production mode not available (removed docker-compose.prod.yaml)"
            shift
            ;;
        --build)
            ACTION="up --build"
            shift
            ;;
        --no-detach)
            DETACHED=false
            shift
            ;;
        --logs)
            ACTION="logs -f"
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --down)
            ACTION="down"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -f, --file FILE       Docker-compose file (default: docker-compose.yaml)"
            echo "  --env-file FILE       Environment variables file (default: .env)"
            echo "  -s, --service NAME    Specify specific service"
            echo "  --prod                Production mode (deprecated)"
            echo "  --build               Rebuild images before starting"
            echo "  --no-detach           Run in foreground mode"
            echo "  --logs                Show logs"
            echo "  --stop                Stop services"
            echo "  --down                Stop and remove containers"
            echo "  --restart             Restart services"
            echo "  -h, --help            Show this help"
            exit 0
            ;;
        *)
            error "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Check for Docker and Docker Compose presence
if ! command -v docker &> /dev/null; then
    error "Docker not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose not installed"
    exit 1
fi

# Determine docker-compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check for compose file presence
if [ ! -f "$COMPOSE_FILE" ]; then
    error "File $COMPOSE_FILE not found"
    exit 1
fi

# Check for .env file presence
if [ ! -f "$ENV_FILE" ] && [ "$ENV_FILE" = ".env" ]; then
    warn "File .env not found. Create it based on env.example"
    if [ -f "env.example" ]; then
        info "Use: cp env.example .env"
    fi
fi

log "Using file: $COMPOSE_FILE"
if [ -n "$SERVICES" ]; then
    log "Service: $SERVICES"
fi

# Execute command
case $ACTION in
    "up --build")
        log "Building and starting services..."
        if [ "$DETACHED" = true ]; then
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build $SERVICES
        else
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up --build $SERVICES
        fi
        ;;
    "up")
        log "Starting services..."
        if [ "$DETACHED" = true ]; then
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $SERVICES
        else
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up $SERVICES
        fi
        ;;
    "logs -f")
        log "Showing logs..."
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f $SERVICES
        ;;
    "stop")
        log "Stopping services..."
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop $SERVICES
        ;;
    "down")
        log "Stopping and removing containers..."
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        ;;
    "restart")
        log "Restarting services..."
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart $SERVICES
        ;;
esac

if [ "$ACTION" = "up" ] || [ "$ACTION" = "up --build" ]; then
    echo ""
    log "Useful commands:"
    echo "  View logs:          $0 --logs"
    echo "  Stop:               $0 --stop"
    echo "  Full stop:          $0 --down"
    echo "  Restart:            $0 --restart"
    echo ""
    info "Container status:"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
fi
