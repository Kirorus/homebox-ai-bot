"""
Admin handling logic
"""

import logging
from aiogram import Router
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class AdminHandler(BaseHandler):
    """Handles admin-related commands"""
    
    def __init__(self, settings, database, homebox_service):
        super().__init__(settings, database)
        self.homebox_service = homebox_service
        self.register_handlers()
    
    def register_handlers(self):
        """Register admin-related handlers"""
        # TODO: Implement admin handlers
        pass
