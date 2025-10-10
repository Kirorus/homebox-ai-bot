"""
Bot handlers module
"""

from .photo_handler import PhotoHandler
from .settings_handler import SettingsHandler
from .admin_handler import AdminHandler
from .base_handler import BaseHandler
from .register_handlers import register_handlers
from .common_handler import CommonHandler

__all__ = ['PhotoHandler', 'SettingsHandler', 'AdminHandler', 'BaseHandler', 'CommonHandler', 'register_handlers']
