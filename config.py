import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')
HOMEBOX_URL = os.getenv('HOMEBOX_URL')
HOMEBOX_TOKEN = os.getenv('HOMEBOX_TOKEN')
HOMEBOX_USER = os.getenv('HOMEBOX_USER')
HOMEBOX_PASSWORD = os.getenv('HOMEBOX_PASSWORD')

# Allowed Telegram users (comma-separated): ALLOWED_USER_IDS=123,456
_ALLOWED = os.getenv('ALLOWED_USER_IDS', '')
try:
    ALLOWED_USER_IDS = {
        int(x.strip()) for x in _ALLOWED.split(',') if x.strip()
    }
except Exception:
    ALLOWED_USER_IDS = set()

# Available LLM models list (adjust to your provider)
AVAILABLE_MODELS = [
    'gpt-4.1-nano','gpt-5','gpt-4.1','gpt-5-nano','gpt-5-chat','gpt-4o-mini','gpt-4o','gpt-5-mini','gpt-4.1-mini',
    'gpt-4-turbo','gpt-4-vision-preview','gpt-5-pro','claude-sonnet-4','claude-sonnet-4.5',
    'claude-opus-4','gemini-2.5-pro','gemini-2.5-flash',
    'gemma-3-4b-it','deepseek-chat-v3-0324','deepseek-r1','deepseek-r1-0528','deepseek-v3.2-exp','deepseek-v3.1-terminus',
    'grok-4'
]

# Default model
DEFAULT_MODEL = os.getenv('OPENAI_MODEL') or 'gpt-4o'

# Location filtering settings
LOCATION_FILTER_MODE = os.getenv('LOCATION_FILTER_MODE', 'marker')  # 'marker', 'all', 'none'
LOCATION_MARKER = os.getenv('LOCATION_MARKER', '[TGB]')  # Marker in location description
