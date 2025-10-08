"""
Handler registration
"""

from aiogram import Dispatcher

from .photo_handler import PhotoHandler
from .settings_handler import SettingsHandler
from .admin_handler import AdminHandler
from .search_handler import SearchHandler


def register_handlers(dp: Dispatcher, settings, database, homebox_service, ai_service, image_service, bot):
    """Register all handlers with the dispatcher"""
    
    # Initialize handlers
    photo_handler = PhotoHandler(settings, database, homebox_service, ai_service, image_service, bot)
    settings_handler = SettingsHandler(settings, database, homebox_service)
    admin_handler = AdminHandler(settings, database, homebox_service)
    search_handler = SearchHandler(settings, database, homebox_service, ai_service, image_service)
    
    # Register routers
    dp.include_router(photo_handler.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(search_handler.router)
