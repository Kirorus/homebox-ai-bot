## HomeBox AI Bot
An AI-powered Telegram bot to add items into your HomeBox. It recognizes items from photos using OpenAI Vision (or compatible APIs), suggests a name/description and a best-fit location, allows manual edits, and creates the item in HomeBox with an optional photo attachment.

### Features
- **Photo recognition**: extract item name, description, and best location from a photo.
- **Pre-submit editing**: edit name, description, and location before adding.
- **HomeBox integration**: creates item and uploads photo to HomeBox.
- **Flexible OpenAI config**: supports custom `base_url` (e.g. Bothub).
- **i18n**: bot messages localized (RU/EN) with per-user language selection.

### Requirements
- Python 3.10+
- Telegram Bot API token
- OpenAI API access or compatible provider (e.g. Bothub)
- Reachable HomeBox server and token (or user/password for login)

### Installation
1) Clone and enter the project directory
```bash
git clone <repo-url>
cd homebox-ai-bot
```
2) Create a virtual environment and install dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3) Configure environment variables (see below). You can copy `sample.env` to `.env`.

### Environment variables (.env)
Copy `sample.env` to `.env` and fill values:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
# Optional: custom OpenAI-compatible endpoint (e.g., Bothub)
OPENAI_BASE_URL=https://bothub.chat/api/v2/openai/v1
HOMEBOX_URL=http://your-homebox-url:7745
HOMEBOX_TOKEN=your_homebox_token
HOMEBOX_USER=your_homebox_username
HOMEBOX_PASSWORD=your_homebox_password
ALLOWED_USER_IDS=123456789,987654321
OPENAI_MODEL=gpt-4o
```
Notes:
- `OPENAI_BASE_URL` is optional; if set, the client targets that base URL.
- `HOMEBOX_URL` is your HomeBox base URL.
- `HOMEBOX_TOKEN` is optional; if missing, the bot tries to login via `HOMEBOX_USER`/`HOMEBOX_PASSWORD` at `/api/v1/users/login` and uses returned `token`.
- `ALLOWED_USER_IDS` is a comma-separated list of Telegram user IDs allowed to use the bot. If empty, bot is open to anyone. Command `/myid` returns your ID.
- `OPENAI_MODEL` overrides the default model used (otherwise the internal default is used).

### Run
```bash
source venv/bin/activate
python bot.py
```
The bot will start polling and handle messages.

### Usage
- Send `/start` to begin. The bot will instruct and wait for a photo.
- Send a photo:
  - The bot analyzes the image via OpenAI Vision,
  - Suggests name/description and best location,
  - Shows inline buttons to edit/confirm.
- Buttons:
  - “✏️ Edit name” — enter a new name.
  - “📝 Edit description” — enter a new description.
  - “📦 Change location” — pick another location.
  - “✅ Confirm and add” — creates the item in HomeBox (photo uploaded as attachment).
  - “❌ Cancel” — cancels and removes the temp photo.
  - “/myid” — replies with your Telegram numeric user ID (available to everyone).
  - `/settings` — choose interface language and model.

### OpenAI and custom providers
The bot uses `openai` SDK with optional custom base URL. Example for Bothub in `.env`:
```env
OPENAI_BASE_URL=https://bothub.chat/api/v2/openai/v1
```
The bot will target that endpoint automatically.

### Architecture
- `bot.py` — Aiogram v3 bot logic: FSM, handlers, OpenAI + HomeBox calls, settings UI.
- `homebox_api.py` — HomeBox client (locations, create item, upload photo; auto-login if needed).
- `config.py` — environment config, available models list, default model, allowed users.
- `i18n.py` — simple i18n helper with RU/EN message catalogs and `t(lang, key, **kwargs)`.
- `requirements.txt` — dependencies.
- `sample.env` — example environment.

### Development
- Stack: `aiogram==3.3.0`, `openai==1.12.0`, `aiohttp==3.9.1`, `python-dotenv==1.0.0`, `httpx==0.27.2`.
- FSM states:
  - `waiting_for_photo`
  - `confirming_data`
  - `editing_name`, `editing_description`, `selecting_location`
- Temp photos are stored on disk and cleaned up on confirm/cancel.

### Tips & troubleshooting
- Verify `.env` values; missing tokens/URLs are common issues.
- If analysis returns defaults, check OpenAI key/limits or `OPENAI_BASE_URL`.
- If adding item fails, check HomeBox response and `HOMEBOX_URL`/`HOMEBOX_TOKEN` or login creds.
- Aiogram 3.x file download methods differ from 2.x — code uses get_file + download by path.
 - To change bot language per user, open `/settings` and choose RU/EN. Defaults to RU on first run.

### Roadmap / ideas
- Persist settings/state in storage/DB instead of memory.
- Highlight selected location in keyboards.
- Reuse a single `aiohttp.ClientSession` across API calls.
- Improve prompts and validation.

### License
MIT (or your preferred license).
