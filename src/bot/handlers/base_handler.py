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
        """Create detailed statistics message with improved formatting and more information"""
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
                uptime = t(lang, 'stats.unknown')
        
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
                last_activity = t(lang, 'stats.unknown')
        
        # Format account created
        account_created = user_stats.get('account_created', 'Unknown')
        if account_created != 'Unknown':
            try:
                created_dt = datetime.fromisoformat(account_created)
                account_created = created_dt.strftime("%Y-%m-%d")
            except:
                account_created = t(lang, 'stats.unknown')
        
        # Get system info
        try:
            process = psutil.Process()
            memory_usage = f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
        except:
            memory_usage = t(lang, 'stats.unknown')
        
        try:
            # Use actual database path from the service for accuracy
            db_size = os.path.getsize(self.database.db_path) / 1024 / 1024
            db_size = f"{db_size:.1f} MB"
        except:
            db_size = t(lang, 'stats.unknown')
        
        # Calculate additional metrics
        total_users = int(bot_stats.get('users_registered', 0))
        total_requests = int(bot_stats.get('total_requests', 0))
        total_items = int(bot_stats.get('items_processed', 0))
        active_24h = int(bot_stats.get('active_users_24h', 0))
        active_7d = int(bot_stats.get('active_users_7d', 0))
        
        # Calculate averages
        avg_requests_per_user = total_requests / total_users if total_users > 0 else 0
        avg_items_per_user = total_items / total_users if total_users > 0 else 0
        
        # Language distribution
        lang_dist = bot_stats.get('language_distribution', {})
        most_popular_lang = ""
        if lang_dist:
            lang_names = {'ru': '🇷🇺 RU', 'en': '🇺🇸 EN', 'de': '🇩🇪 DE', 'fr': '🇫🇷 FR', 'es': '🇪🇸 ES'}
            sorted_langs = sorted(lang_dist.items(), key=lambda x: x[1], reverse=True)
            if sorted_langs:
                lang_code, count = sorted_langs[0]
                lang_name = lang_names.get(lang_code, lang_code.upper())
                most_popular_lang = f"{lang_name} ({count})"
        
        # Model distribution
        model_dist = bot_stats.get('model_distribution', {})
        most_popular_model = ""
        if model_dist:
            sorted_models = sorted(model_dist.items(), key=lambda x: x[1], reverse=True)
            if sorted_models:
                model_name, count = sorted_models[0]
                most_popular_model = f"`{model_name}` ({count})"
        
        # Format model name for user
        model_name = escape_markdown(user_settings.get('model', t(lang, 'stats.unknown')))
        
        # Create the improved statistics message
        return (
            f"🎯 **{t(lang, 'stats.title')}**\n"
            f"{'=' * 25}\n\n"
            
            f"👤 **{t(lang, 'stats.user_activity')}**\n"
            f"├ {t(lang, 'stats.photos_analyzed')}: `{user_stats.get('photos_analyzed', 0)}`\n"
            f"├ {t(lang, 'stats.reanalyses')}: `{user_stats.get('reanalyses', 0)}`\n"
            f"├ {t(lang, 'stats.last_activity')}: `{last_activity}`\n"
            f"└ {t(lang, 'stats.account_created')}: `{account_created}`\n\n"
            
            f"⚙️ **{t(lang, 'stats.current_settings')}**\n"
            f"├ {t(lang, 'stats.bot_language')}: `{user_settings.get('bot_lang', 'Unknown').upper()}`\n"
            f"├ {t(lang, 'stats.gen_language')}: `{user_settings.get('gen_lang', 'Unknown').upper()}`\n"
            f"└ {t(lang, 'stats.ai_model')}: `{model_name}`\n\n"
            
            f"📊 **General Statistics**\n"
            f"├ {t(lang, 'stats.users')}: `{total_users}`\n"
            f"├ {t(lang, 'stats.total_requests')}: `{total_requests}`\n"
            f"├ {t(lang, 'stats.items_processed')}: `{total_items}`\n"
            f"├ {t(lang, 'stats.active_users_24h')}: `{active_24h}`\n"
            f"├ {t(lang, 'stats.active_users_7d')}: `{active_7d}`\n"
            f"├ {t(lang, 'stats.avg_requests_per_user')}: `{avg_requests_per_user:.1f}`\n"
            f"└ {t(lang, 'stats.avg_items_per_user')}: `{avg_items_per_user:.1f}`\n\n"
            
            f"🌍 **Popularity**\n"
            f"├ {t(lang, 'stats.most_popular_lang')}: `{most_popular_lang if most_popular_lang else t(lang, 'stats.unknown')}`\n"
            f"└ {t(lang, 'stats.most_popular_model')}: `{most_popular_model if most_popular_model else t(lang, 'stats.unknown')}`\n\n"
            
            f"🖥️ **{t(lang, 'stats.system_info')}**\n"
            f"├ {t(lang, 'stats.uptime')}: `{uptime}`\n"
            f"├ {t(lang, 'stats.database_size')}: `{db_size}`\n"
            f"├ {t(lang, 'stats.memory_usage')}: `{memory_usage}`\n"
            f"└ {t(lang, 'stats.status')}: `{t(lang, 'stats.online')}`\n\n"
            
            f"📈 **Detailed Language Statistics:**\n"
            f"{self._format_language_distribution(lang_dist, lang)}\n\n"
            
            f"🤖 **Detailed Model Statistics:**\n"
            f"{self._format_model_distribution(model_dist)}"
        )
    
    def _format_language_distribution(self, lang_dist: dict, lang: str) -> str:
        """Format language distribution with visual bars"""
        if not lang_dist:
            return f"`{t(lang, 'stats.unknown')}`"
        
        lang_names = {'ru': '🇷🇺 RU', 'en': '🇺🇸 EN', 'de': '🇩🇪 DE', 'fr': '🇫🇷 FR', 'es': '🇪🇸 ES'}
        total_users = sum(int(count) for count in lang_dist.values())
        
        formatted_items = []
        for lang_code, count in sorted(lang_dist.items(), key=lambda x: int(x[1]), reverse=True):
            lang_name = lang_names.get(lang_code, lang_code.upper())
            count_int = int(count)
            percentage = (count_int / total_users * 100) if total_users > 0 else 0
            bar_length = int(percentage / 5)  # Each character represents 5%
            bar = "█" * bar_length + "░" * (20 - bar_length)
            formatted_items.append(f"├ {lang_name}: `{count_int}` ({percentage:.1f}%) {bar}")
        
        return "\n".join(formatted_items)
    
    def _format_model_distribution(self, model_dist: dict) -> str:
        """Format model distribution with visual bars"""
        if not model_dist:
            return f"`{t('en', 'stats.unknown')}`"
        
        total_users = sum(int(count) for count in model_dist.values())
        
        formatted_items = []
        for model, count in sorted(model_dist.items(), key=lambda x: int(x[1]), reverse=True):
            count_int = int(count)
            percentage = (count_int / total_users * 100) if total_users > 0 else 0
            bar_length = int(percentage / 5)  # Each character represents 5%
            bar = "█" * bar_length + "░" * (20 - bar_length)
            formatted_items.append(f"├ `{model}`: `{count_int}` ({percentage:.1f}%) {bar}")
        
        return "\n".join(formatted_items)

    def create_quick_stats_message(self, lang: str, bot_stats: dict, user_stats: dict, user_settings: dict) -> str:
        """Create a compact statistics message focusing on essentials with improved formatting"""
        from datetime import datetime
        
        # Simple aggregates with fallbacks
        photos = int(user_stats.get('photos_analyzed', 0))
        rean = int(user_stats.get('reanalyses', 0))
        users = int(bot_stats.get('users_registered', 0))
        items = int(bot_stats.get('items_processed', 0))
        active_24h = int(bot_stats.get('active_users_24h', 0))
        model = user_settings.get('model', 'Unknown')
        
        # Escape model for markdown inline code
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
                uptime_brief = t(lang, 'stats.unknown')
        else:
            uptime_brief = t(lang, 'stats.unknown')
        
        return (
            f"⚡ **{t(lang, 'stats.title')}**\n"
            f"{'─' * 20}\n\n"
            f"👤 **{t(lang, 'stats.user_activity')}**\n"
            f"├ {t(lang, 'stats.photos_analyzed')}: `{photos}`\n"
            f"└ {t(lang, 'stats.reanalyses')}: `{rean}`\n\n"
            f"🌐 **General Statistics**\n"
            f"├ {t(lang, 'stats.users')}: `{users}`\n"
            f"├ {t(lang, 'stats.items_processed')}: `{items}`\n"
            f"├ {t(lang, 'stats.active_users_24h')}: `{active_24h}`\n"
            f"└ {t(lang, 'stats.uptime')}: `{uptime_brief}`\n\n"
            f"⚙️ **{t(lang, 'stats.ai_model')}**: `{model_md}`"
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
