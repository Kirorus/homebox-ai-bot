# HomeBox AI Bot

[![CI](https://github.com/Kirorus/homebox-ai-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/Kirorus/homebox-ai-bot/actions/workflows/tests.yml) [![Docker Build](https://github.com/Kirorus/homebox-ai-bot/actions/workflows/docker-build.yml/badge.svg)](https://github.com/Kirorus/homebox-ai-bot/actions/workflows/docker-build.yml) [![codecov](https://codecov.io/gh/Kirorus/homebox-ai-bot/branch/main/graph/badge.svg)](https://app.codecov.io/gh/Kirorus/homebox-ai-bot) [![Docker Pulls](https://img.shields.io/docker/pulls/kirorus/homebox-ai-bot.svg)](https://hub.docker.com/r/kirorus/homebox-ai-bot) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Smart Telegram bot that uses AI vision to add items to your HomeBox inventory from photos. Send a photo → get name, description, and suggested storage location → confirm → item is created in HomeBox with the photo attached.

## ✨ Highlights
- AI photo recognition and smart suggestions
- Direct HomeBox integration (items, locations, attachments)
- Multi-language UI (EN, RU, DE, FR, ES)
- Access control and robust error handling

## 🚀 Quick Start

### 1) Docker (recommended)
```bash
cp env.example .env
docker-compose up -d

# Logs
docker-compose logs -f homebox-ai-bot
```

### 2) Local run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
python src/main.py
```

## ⚙️ Configuration (.env)
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://bothub.chat/api/v2/openai/v1

HOMEBOX_URL=http://your-homebox-url:7745
HOMEBOX_USER=your_homebox_username
HOMEBOX_PASSWORD=your_homebox_password

ALLOWED_USER_IDS=123456789,987654321
```

Notes:
- Use `OPENAI_BASE_URL` for compatible providers (e.g., Bothub)
- Authentication uses HOMEBOX_USER and HOMEBOX_PASSWORD
- If `ALLOWED_USER_IDS` is empty, bot allows all users

## 🐳 Docker
- Pulls published image `kirorus/homebox-ai-bot:latest`
- Single service `docker-compose.yaml` (bot only)
- Volumes: `./data`, `./logs`, `./temp`
- Healthcheck and log rotation configured

Run via compose:
```bash
./scripts/docker-deploy.sh           # up -d
./scripts/docker-deploy.sh --logs    # follow logs
./scripts/docker-deploy.sh --down    # stop & remove
```

CI/CD:
- GitHub Actions builds and pushes Docker image to Docker Hub on push
- Multi-arch build (linux/amd64, linux/arm64) with security scan

## 📖 Commands
User: `/start`, `/settings`, `/search`, `/recent`, `/myid`

Admin: `/stats`, `/cleanup`, `/checkapi`, `/testupload`

## 📂 Structure
```
src/
  bot/            # Handlers, keyboards, states
  services/       # AI, HomeBox, DB, image
  models/         # Pydantic models
  config/         # Settings loading/validation
  utils/          # Helpers
  main.py         # Entry point
```

## 📝 License
MIT
<!-- ci: refresh docker hub description -->