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
./init-volumes.sh          # Initialize volume directories
docker-compose up -d

# Logs
docker-compose logs -f homebox-ai-bot
```

### 2) Local run
```bash
# Using Make (recommended)
make venv env run

# Or manually
python -m venv .venv && source .venv/bin/activate
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
make compose-up                       # start services
make compose-down                     # stop services
docker-compose logs -f homebox-ai-bot # follow logs
```

CI/CD:
- GitHub Actions builds and pushes Docker image to Docker Hub on push
- Multi-arch build (linux/amd64, linux/arm64) with security scan

## 📖 Commands
User commands:
- `/start` - Start the bot and show main menu
- `/settings` - Configure bot settings
- `/search` - Search for items in HomeBox
- `/recent` - Show recently added items
- `/myid` - Get your Telegram user ID

Bot workflow:
1. Send a photo of an item
2. Bot analyzes the image using AI
3. Bot suggests name, description, and storage location
4. Confirm or edit the suggestions
5. Item is automatically added to HomeBox

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

## 🔧 Troubleshooting

### Common Issues

**Bot not responding:**
- Check if bot token is correct in `.env`
- Verify HomeBox URL and credentials
- Check logs: `docker-compose logs -f homebox-ai-bot`

**AI not working:**
- Verify OpenAI API key and base URL
- Check if API provider is accessible
- Ensure sufficient API credits

**Permission denied errors:**
- Check file permissions for `data/`, `logs/`, `temp/` directories
- Ensure Docker volumes are properly mounted

**Database issues:**
- Check if SQLite database is accessible
- Verify database file permissions

### Development

**Running tests:**
```bash
make test                    # Run all tests
make coverage               # Generate coverage report
```

**Code quality:**
```bash
make format                 # Format code with black
make lint                   # Lint with flake8
make check                  # Run tests and i18n checks
```

**Local development:**
```bash
make venv env run           # Setup and start bot
make stop                   # Stop bot
make restart                # Restart bot
```

**Docker development:**
```bash
make docker-build          # Build image
make compose-up            # Start with docker-compose
make compose-down          # Stop services
```

## 📝 License
MIT
<!-- ci: refresh docker hub description -->