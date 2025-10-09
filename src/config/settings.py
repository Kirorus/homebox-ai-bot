"""
Configuration settings with validation
"""

import os
from dataclasses import dataclass
from typing import List, Set, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AISettings:
    """AI service configuration"""
    api_key: str
    base_url: Optional[str] = None
    default_model: str = 'gpt-4o'
    available_models: List[str] = None
    
    def __post_init__(self):
        if self.available_models is None:
            # Only models that support image analysis
            self.available_models = [
                'gpt-5-chat', 'gpt-5-nano', 'gpt-5', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4-vision-preview',
                'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229',
                'claude-3-sonnet-20240229', 'claude-3-haiku-20240307',
                'gemini-1.5-pro', 'gemini-1.5-flash'
            ]
        
        # Validate API key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Validate model
        if self.default_model not in self.available_models:
            raise ValueError(f"Default model {self.default_model} not in available models")


@dataclass
class HomeBoxSettings:
    """HomeBox API configuration"""
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    location_filter_mode: str = 'marker'
    location_marker: str = '[TGB]'
    
    def __post_init__(self):
        # Validate URL
        if not self.url:
            raise ValueError("HomeBox URL is required")
        
        # Ensure URL doesn't end with slash
        self.url = self.url.rstrip('/')
        
        # Validate authentication (username/password only)
        if not (self.username and self.password):
            raise ValueError("Username and password must be provided for HomeBox authentication")
        
        # Validate filter mode
        if self.location_filter_mode not in ['marker', 'all', 'none']:
            raise ValueError("Location filter mode must be 'marker', 'all', or 'none'")


@dataclass
class BotSettings:
    """Bot configuration"""
    token: str
    allowed_user_ids: Set[int] = None
    debug_mode: bool = False
    log_level: str = 'INFO'
    
    def __post_init__(self):
        # Validate token
        if not self.token:
            raise ValueError("Telegram bot token is required")
        
        if self.allowed_user_ids is None:
            self.allowed_user_ids = set()
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        
        self.log_level = self.log_level.upper()


@dataclass
class Settings:
    """Main configuration settings"""
    ai: AISettings
    homebox: HomeBoxSettings
    bot: BotSettings
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables"""
        # Parse allowed user IDs
        allowed_users_str = os.getenv('ALLOWED_USER_IDS', '')
        allowed_user_ids = set()
        if allowed_users_str:
            try:
                allowed_user_ids = {
                    int(x.strip()) for x in allowed_users_str.split(',') if x.strip()
                }
            except ValueError:
                raise ValueError("Invalid ALLOWED_USER_IDS format. Use comma-separated integers.")
        
        return cls(
            ai=AISettings(
                api_key=os.getenv('OPENAI_API_KEY', ''),
                base_url=os.getenv('OPENAI_BASE_URL'),
                default_model=os.getenv('OPENAI_MODEL', 'gpt-4o')
            ),
            homebox=HomeBoxSettings(
                url=os.getenv('HOMEBOX_URL', ''),
                username=os.getenv('HOMEBOX_USER'),
                password=os.getenv('HOMEBOX_PASSWORD'),
                location_filter_mode=os.getenv('LOCATION_FILTER_MODE', 'marker'),
                location_marker=os.getenv('LOCATION_MARKER', '[TGB]')
            ),
            bot=BotSettings(
                token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
                allowed_user_ids=allowed_user_ids,
                debug_mode=os.getenv('DEBUG', 'false').lower() == 'true',
                log_level=os.getenv('LOG_LEVEL', 'INFO')
            )
        )
