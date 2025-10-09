# Docker Deployment Guide

This document describes how to deploy HomeBox AI Bot using Docker.

## 🐳 Quick Start

### 1. Environment Setup

```bash
# Copy environment variables file
cp env.example .env

# Edit .env file with your settings
nano .env
```

### 2. Run with Docker Compose

```bash
# Run in background mode
./scripts/docker-deploy.sh

# Or manually
docker-compose up -d
```

### 3. View Logs

```bash
# Using script
./scripts/docker-deploy.sh --logs

# Or manually
docker-compose logs -f homebox-ai-bot
```

## 🔧 Available Commands

### docker-deploy.sh Script

```bash
# Run
./scripts/docker-deploy.sh [OPTIONS]

# Options:
--prod              # Use production configuration (deprecated)
--build             # Rebuild images
--no-detach         # Run in foreground mode
--logs              # Show logs
--stop              # Stop services
--down              # Full stop with container removal
--restart           # Restart services
-s, --service NAME  # Specify specific service
```

### docker-build.sh Script

```bash
# Local image building
./scripts/docker-build.sh [OPTIONS]

# Options:
-n, --name NAME     # Image name
-t, --tag TAG       # Image tag
--no-cache          # Build without cache
--pull              # Update base image
```

## 📁 File Structure

```
├── Dockerfile                 # Main Docker image
├── docker-compose.yaml        # Development and production
├── .dockerignore              # Build exclusions
├── env.example                # Environment variables example
└── scripts/
    ├── docker-build.sh        # Build script
    └── docker-deploy.sh       # Deployment script
```

## 🌍 Environment Variables

### Required

- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `OPENAI_API_KEY` - OpenAI API key
- `HOMEBOX_URL` - HomeBox server URL
- `HOMEBOX_TOKEN` - HomeBox token (or login/password)
- `ALLOWED_USER_IDS` - Allowed user IDs

### Optional

- `OPENAI_BASE_URL` - Base URL for OpenAI API
- `HOMEBOX_USER` - HomeBox user
- `HOMEBOX_PASSWORD` - HomeBox password

## 🚀 Deployment

### Development and Production

```bash
# Run bot
docker-compose up -d

# View logs
docker-compose logs -f

# Or using script
./scripts/docker-deploy.sh
```

## 🔍 Monitoring

### Status Check

```bash
# Container status
docker-compose ps

# Resource usage
docker stats

# Service logs
docker-compose logs homebox-ai-bot
```

### Health Check

Bot has built-in health check:

```bash
# Check status
docker inspect homebox-ai-bot | grep Health -A 10
```

## 🛠️ Troubleshooting

### HomeBox Connection Issues

```bash
# Check HomeBox availability
docker exec homebox-ai-bot ping your-homebox-url

# Check environment variables
docker exec homebox-ai-bot env | grep HOMEBOX
```

### Database Issues

```bash
# Check data folder permissions
ls -la data/

# Recreate database
docker-compose down
rm -rf data/*
docker-compose up -d
```

### Log Issues

```bash
# Clean logs
docker system prune -f

# Check log size
docker system df
```

## 🔄 Updates

### Image Updates

```bash
# Stop
docker-compose down

# Update image
docker-compose pull

# Start
docker-compose up -d
```

### Code Updates

```bash
# Rebuild and start
./scripts/docker-deploy.sh --build
```

## 📦 GitHub Actions

Automatic build and upload to Docker Hub is configured via GitHub Actions:

- **Triggers**: push to main/master/develop, tag creation
- **Registry**: Docker Hub (requires secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`)
- **Tags**: latest, branch-name, semver
- **Platforms**: linux/amd64, linux/arm64

### GitHub Secrets Setup

1. Go to Settings → Secrets and variables → Actions
2. Add:
   - `DOCKERHUB_USERNAME` - your Docker Hub username
   - `DOCKERHUB_TOKEN` - Docker Hub token

## 🧪 Testing

```bash
# Run tests in container
docker-compose exec homebox-ai-bot python -m pytest

# Check configuration
docker-compose exec homebox-ai-bot python -c "from config import load_settings; print(load_settings())"
```

## 📝 Logs

Logs are saved to:
- Container: `/app/logs/bot.log`
- Host: `./logs/bot.log`

Log rotation is configured in docker-compose (max 10MB, 3 files).
