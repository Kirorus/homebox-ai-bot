"""
Base handler class
"""

import logging
from abc import ABC
from typing import Optional

from aiogram import Router
from aiogram.types import Message, CallbackQuery

from config.settings import Settings
from models.user import User, UserSettings
from services.database_service import DatabaseService
from i18n.i18n_manager import t

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Base handler class with common functionality"""
    
    def __init__(self, settings: Settings, database: DatabaseService):
        self.settings = settings
        self.database = database
        self.router = Router()
    
    async def get_user_settings(self, user_id: int) -> UserSettings:
        """Get user settings"""
        try:
            settings_data = await self.database.get_user_settings(user_id)
            if settings_data:
                return UserSettings.from_dict(settings_data)
            else:
                # Create default settings for new user
                default_settings = UserSettings(user_id=user_id)
                await self.database.set_user_settings(user_id, default_settings.to_dict())
                return default_settings
        except Exception as e:
            logger.error(f"Failed to get user settings for {user_id}: {e}")
            return UserSettings(user_id=user_id)
    
    async def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        if not self.settings.bot.allowed_user_ids:
            return True  # No restrictions
        return user_id in self.settings.bot.allowed_user_ids
    
    async def log_user_action(self, action: str, user_id: int, details: dict = None):
        """Log user action"""
        action_info = {
            'action': action,
            'user_id': user_id,
            'details': details or {}
        }
        logger.info(f"User action: {action} by user {user_id}", extra=action_info)
    
    async def handle_error(self, error: Exception, context: str, user_id: Optional[int] = None):
        """Handle errors with logging"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id
        }
        logger.error(f"Error in {context}: {error}", extra=error_info)
    
    def create_beautiful_start_message(self, lang: str) -> str:
        """Create beautiful start message with formatting"""
        # Create progress bar for features
        def create_progress_bar(current: int, total: int, width: int = 10) -> str:
            filled = int((current / total) * width)
            bar = "█" * filled + "░" * (width - filled)
            return f"`{bar}` {current}/{total}"
        
        # Create feature list with progress indicators
        features = [
            t(lang, 'start.features.ai_analysis'),
            t(lang, 'start.features.auto_location'),
            t(lang, 'start.features.multi_lang'),
            t(lang, 'start.features.smart_org')
        ]
        
        feature_list = ""
        for i, feature in enumerate(features, 1):
            feature_list += f"  {create_progress_bar(i, len(features))} {feature}\n"
        
        # Create the main message
        message = f"""
{t(lang, 'start.welcome')}

**{t(lang, 'start.subtitle')}**

{t(lang, 'start.description')}

**✨ {t(lang, 'start.features.ai_analysis')}**
{feature_list}

{t(lang, 'start.commands')}
{t(lang, 'start.commands_list')}

{t(lang, 'start.get_started')}
        """.strip()
        
        return message
    
    def create_progress_message(self, lang: str, step: int, total_steps: int, current_action: str) -> str:
        """Create progress message with visual progress bar"""
        def create_progress_bar(current: int, total: int, width: int = 15) -> str:
            filled = int((current / total) * width)
            bar = "█" * filled + "░" * (width - filled)
            return f"`{bar}` {current}/{total}"
        
        progress_bar = create_progress_bar(step, total_steps)
        step_name = t(lang, f'processing.steps.{step}')
        
        return f"""
{current_action}

{progress_bar} **{step_name}**

{t(lang, 'processing.please_wait')}
        """.strip()
    
    def register_handlers(self):
        """Register handlers - to be implemented by subclasses"""
        pass
