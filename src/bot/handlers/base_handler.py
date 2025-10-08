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
        """Create concise and informative start message"""
        # Create the main message
        message = f"""
{t(lang, 'start.welcome')}

{t(lang, 'start.description')}

**{t(lang, 'start.how_it_works')}**
{t(lang, 'start.step1')}
{t(lang, 'start.step2')}
{t(lang, 'start.step3')}
{t(lang, 'start.step4')}

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
        
        # Add animated loading indicator
        loading_icons = ["⏳", "🔄", "⚡", "✨"]
        loading_icon = loading_icons[step % len(loading_icons)]
        
        return f"""
{loading_icon} **{current_action}**

{progress_bar} **{step_name}**

{t(lang, 'processing.please_wait')}
        """.strip()
    
    def create_loading_message(self, lang: str, action: str) -> str:
        """Create animated loading message"""
        loading_icons = ["⏳", "🔄", "⚡", "✨", "🌟", "💫"]
        import random
        icon = random.choice(loading_icons)
        
        return f"""
{icon} **{action}**

{t(lang, 'processing.please_wait')}
        """.strip()
    
    def create_success_message(self, lang: str, title: str, message: str, details: str = None) -> str:
        """Create success message with formatting"""
        success_icons = ["✅", "🎉", "✨", "🌟", "💫", "🔥"]
        import random
        icon = random.choice(success_icons)
        
        result = f"""
{icon} **{title}**

{message}
        """.strip()
        
        if details:
            result += f"\n\n**{t(lang, 'common.details')}:**\n{details}"
        
        return result
    
    def create_error_message(self, lang: str, title: str, message: str, suggestion: str = None) -> str:
        """Create error message with formatting"""
        error_icons = ["❌", "⚠️", "🚫", "💥", "🔥"]
        import random
        icon = random.choice(error_icons)
        
        result = f"""
{icon} **{title}**

{message}
        """.strip()
        
        if suggestion:
            result += f"\n\n**{t(lang, 'common.suggestion')}:**\n{suggestion}"
        
        return result
    
    def create_detailed_stats_message(self, lang: str, bot_stats: dict, user_stats: dict, user_settings: dict) -> str:
        """Create detailed statistics message"""
        import os
        import psutil
        from datetime import datetime
        
        # Format uptime
        uptime = bot_stats.get('start_time', 'Unknown')
        if uptime != 'Unknown':
            try:
                start_time = datetime.fromisoformat(uptime)
                uptime_delta = datetime.now() - start_time
                days = uptime_delta.days
                hours, remainder = divmod(uptime_delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                uptime = f"{days}d {hours}h {minutes}m"
            except:
                uptime = "Unknown"
        
        # Format last activity
        last_activity = user_stats.get('last_activity', 'Unknown')
        if last_activity != 'Unknown':
            try:
                last_activity_dt = datetime.fromisoformat(last_activity)
                last_activity_delta = datetime.now() - last_activity_dt
                if last_activity_delta.days > 0:
                    last_activity = f"{last_activity_delta.days} days ago"
                elif last_activity_delta.seconds > 3600:
                    hours = last_activity_delta.seconds // 3600
                    last_activity = f"{hours} hours ago"
                else:
                    minutes = last_activity_delta.seconds // 60
                    last_activity = f"{minutes} minutes ago"
            except:
                last_activity = "Unknown"
        
        # Format account created
        account_created = user_stats.get('account_created', 'Unknown')
        if account_created != 'Unknown':
            try:
                created_dt = datetime.fromisoformat(account_created)
                account_created = created_dt.strftime("%Y-%m-%d")
            except:
                account_created = "Unknown"
        
        # Get system info
        try:
            process = psutil.Process()
            memory_usage = f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
        except:
            memory_usage = "Unknown"
        
        try:
            db_size = os.path.getsize("../bot_data.db") / 1024 / 1024
            db_size = f"{db_size:.1f} MB"
        except:
            db_size = "Unknown"
        
        # Language distribution
        lang_dist = bot_stats.get('language_distribution', {})
        lang_dist_text = ""
        if lang_dist:
            lang_names = {'ru': '🇷🇺 RU', 'en': '🇺🇸 EN', 'de': '🇩🇪 DE', 'fr': '🇫🇷 FR', 'es': '🇪🇸 ES'}
            lang_items = []
            for lang_code, count in sorted(lang_dist.items(), key=lambda x: x[1], reverse=True):
                lang_name = lang_names.get(lang_code, lang_code.upper())
                lang_items.append(f"{lang_name}: {count}")
            lang_dist_text = "\n".join(lang_items)
        
        # Model distribution
        model_dist = bot_stats.get('model_distribution', {})
        model_dist_text = ""
        if model_dist:
            model_items = []
            for model, count in sorted(model_dist.items(), key=lambda x: x[1], reverse=True):
                model_items.append(f"`{model}`: {count}")
            model_dist_text = "\n".join(model_items)
        
        return f"""
{t(lang, 'stats.title')}

**{t(lang, 'stats.user_activity')}**
{t(lang, 'stats.photos_analyzed')}: {user_stats.get('photos_analyzed', 0)}
{t(lang, 'stats.reanalyses')}: {user_stats.get('reanalyses', 0)}
{t(lang, 'stats.last_activity')}: {last_activity}
{t(lang, 'stats.account_created')}: {account_created}

**{t(lang, 'stats.current_settings')}**
{t(lang, 'stats.bot_language')}: {user_settings.get('bot_lang', 'Unknown').upper()}
{t(lang, 'stats.gen_language')}: {user_settings.get('gen_lang', 'Unknown').upper()}
{t(lang, 'stats.ai_model')}: `{user_settings.get('model', 'Unknown')}`

**{t(lang, 'stats.users')}**: {bot_stats.get('users_registered', 0)}
**{t(lang, 'stats.items_processed')}**: {bot_stats.get('items_processed', 0)}
**{t(lang, 'stats.total_requests')}**: {bot_stats.get('total_requests', 0)}
**{t(lang, 'stats.uptime')}**: {uptime}

**{t(lang, 'stats.system_info')}**
{t(lang, 'stats.database_size')}: {db_size}
{t(lang, 'stats.memory_usage')}: {memory_usage}
{t(lang, 'stats.status')}: {t(lang, 'stats.online')}

**Language Distribution:**
{lang_dist_text if lang_dist_text else "No data"}

**Model Distribution:**
{model_dist_text if model_dist_text else "No data"}
        """.strip()
    
    def register_handlers(self):
        """Register handlers - to be implemented by subclasses"""
        pass
