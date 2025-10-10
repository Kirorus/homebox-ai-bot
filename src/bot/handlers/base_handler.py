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

    async def send_or_edit(self, origin: Message | CallbackQuery, text: str, reply_markup=None, parse_mode: str | None = None):
        """Prefer editing the current message, fall back to sending a new one."""
        try:
            if isinstance(origin, CallbackQuery):
                await origin.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                return origin.message
            else:
                await origin.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                return origin
        except Exception:
            try:
                if isinstance(origin, CallbackQuery):
                    return await origin.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                else:
                    return await origin.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception:
                logger.exception("Failed to send_or_edit message")
                return None

    async def try_delete(self, obj: Message | CallbackQuery):
        """Attempt to delete a message; ignore failures."""
        try:
            if isinstance(obj, CallbackQuery):
                await obj.message.delete()
            else:
                await obj.delete()
        except Exception:
            pass
    
    def create_detailed_stats_message(self, lang: str, bot_stats: dict, user_stats: dict, user_settings: dict) -> str:
        """Create detailed statistics message"""
        import os
        import psutil
        from datetime import datetime
        
        def escape_markdown(text: str) -> str:
            if not isinstance(text, str):
                text = str(text)
            return text.replace('\\', '\\\\') \
                       .replace('_', '\\_') \
                       .replace('*', '\\*') \
                       .replace('[', '\\[') \
                       .replace(']', '\\]') \
                       .replace('(', '\\(') \
                       .replace(')', '\\)') \
                       .replace('~', '\\~') \
                       .replace('`', '\\`') \
                       .replace('>', '\\>') \
                       .replace('#', '\\#') \
                       .replace('+', '\\+') \
                       .replace('-', '\\-') \
                       .replace('=', '\\=') \
                       .replace('|', '\\|') \
                       .replace('{', '\\{') \
                       .replace('}', '\\}') \
                       .replace('.', '\\.') \
                       .replace('!', '\\!')
        
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
            db_size = os.path.getsize("../data/bot_data.db") / 1024 / 1024
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
        
        model_name = escape_markdown(user_settings.get('model', 'Unknown'))
        return (
            f"{t(lang, 'stats.title')}\n\n"
            f"**{t(lang, 'stats.user_activity')}**\n"
            f"{t(lang, 'stats.photos_analyzed')}: {user_stats.get('photos_analyzed', 0)}\n"
            f"{t(lang, 'stats.reanalyses')}: {user_stats.get('reanalyses', 0)}\n"
            f"{t(lang, 'stats.last_activity')}: {last_activity}\n"
            f"{t(lang, 'stats.account_created')}: {account_created}\n\n"
            f"**{t(lang, 'stats.current_settings')}**\n"
            f"{t(lang, 'stats.bot_language')}: {user_settings.get('bot_lang', 'Unknown').upper()}\n"
            f"{t(lang, 'stats.gen_language')}: {user_settings.get('gen_lang', 'Unknown').upper()}\n"
            f"{t(lang, 'stats.ai_model')}: `{model_name}`\n\n"
            f"**{t(lang, 'stats.users')}**: {bot_stats.get('users_registered', 0)}\n"
            f"**{t(lang, 'stats.items_processed')}**: {bot_stats.get('items_processed', 0)}\n"
            f"**{t(lang, 'stats.total_requests')}**: {bot_stats.get('total_requests', 0)}\n"
            f"**{t(lang, 'stats.uptime')}**: {uptime}\n\n"
            f"**{t(lang, 'stats.system_info')}**\n"
            f"{t(lang, 'stats.database_size')}: {db_size}\n"
            f"{t(lang, 'stats.memory_usage')}: {memory_usage}\n"
            f"{t(lang, 'stats.status')}: {t(lang, 'stats.online')}\n\n"
            f"**Language Distribution:**\n"
            f"{lang_dist_text if lang_dist_text else 'No data'}\n\n"
            f"**Model Distribution:**\n"
            f"{model_dist_text if model_dist_text else 'No data'}"
        )

    def create_quick_stats_message(self, lang: str, bot_stats: dict, user_stats: dict, user_settings: dict) -> str:
        """Create a compact statistics message focusing on essentials"""
        from datetime import datetime
        # Simple aggregates with fallbacks
        photos = user_stats.get('photos_analyzed', 0)
        rean = user_stats.get('reanalyses', 0)
        users = bot_stats.get('users_registered', 0)
        items = bot_stats.get('items_processed', 0)
        model = user_settings.get('model', 'Unknown')
        # escape model for markdown inline code
        def escape_md(text: str) -> str:
            if not isinstance(text, str):
                text = str(text)
            return text.replace('`', '\\`').replace('_', '\\_').replace('*', '\\*')
        model_md = escape_md(model)
        # Uptime brief
        uptime = bot_stats.get('start_time')
        if uptime:
            try:
                start = datetime.fromisoformat(uptime)
                delta = datetime.now() - start
                days = delta.days
                hours = (delta.seconds // 3600)
                uptime_brief = f"{days}d {hours}h"
            except Exception:
                uptime_brief = t(lang, 'stats.unknown') if 'stats.unknown' in self._safe_keys(lang) else 'Unknown'
        else:
            uptime_brief = t(lang, 'stats.unknown') if 'stats.unknown' in self._safe_keys(lang) else 'Unknown'
        return (
            f"**{t(lang, 'stats.title')}**\n\n"
            f"👤 {t(lang, 'stats.photos_analyzed')}: {photos} | {t(lang, 'stats.reanalyses')}: {rean}\n"
            f"🧠 {t(lang, 'stats.ai_model')}: `{model_md}` | ⏰ {t(lang, 'stats.uptime')}: {uptime_brief}\n"
            f"👥 {t(lang, 'stats.users')}: {users} | 📦 {t(lang, 'stats.items_processed')}: {items}"
        )

    def _safe_keys(self, lang: str) -> set:
        """Internal helper to avoid KeyError if i18n misses; assumes i18n manager can expose keys; fallback empty."""
        try:
            # i18n manager may not expose keys; return empty to avoid dependency
            return set()
        except Exception:
            return set()
    
    def register_handlers(self):
        """Register handlers - to be implemented by subclasses"""
        pass
