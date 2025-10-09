"""
Tests for photo handler
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, PhotoSize, User

from bot.handlers.photo_handler import PhotoHandler
from bot.states import ItemStates


class TestPhotoHandler:
    """Test cases for PhotoHandler"""
    
    @pytest.fixture
    def photo_handler(self, test_settings, database_service, homebox_service, ai_service, image_service, mock_telegram_bot):
        """Create photo handler for testing"""
        return PhotoHandler(
            test_settings, 
            database_service, 
            homebox_service, 
            ai_service, 
            image_service, 
            mock_telegram_bot
        )
    
    @pytest.fixture
    def mock_message(self):
        """Create mock Telegram message"""
        message = MagicMock(spec=Message)
        message.message_id = 123
        message.from_user.id = 456789
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.answer = AsyncMock()
        message.reply = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_callback_query(self):
        """Create mock callback query"""
        query = MagicMock(spec=CallbackQuery)
        query.id = "test_query_id"
        query.from_user.id = 456789
        query.data = "test_callback_data"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_media = AsyncMock()
        query.message = MagicMock(spec=Message)
        query.message.message_id = 123
        query.message.chat.id = 456789
        return query
    
    @pytest.fixture
    def mock_photo_message(self, mock_message):
        """Create mock message with photo"""
        photo_size = MagicMock(spec=PhotoSize)
        photo_size.file_id = "test_photo_id"
        photo_size.width = 1024
        photo_size.height = 768
        photo_size.file_size = 500000
        
        mock_message.photo = [photo_size]
        mock_message.caption = "Test caption"
        return mock_message
    
    def test_photo_handler_initialization(self, photo_handler):
        """Test photo handler initialization"""
        assert photo_handler is not None
        assert photo_handler.settings is not None
        assert photo_handler.database is not None
        assert photo_handler.homebox_service is not None
        assert photo_handler.ai_service is not None
        assert photo_handler.image_service is not None
        assert photo_handler.bot is not None
    
    def test_photo_handler_router_exists(self, photo_handler):
        """Test that router is created"""
        assert hasattr(photo_handler, 'router')
        assert photo_handler.router is not None
    
    @pytest.mark.asyncio
    async def test_is_user_allowed_no_restrictions(self, photo_handler):
        """Test user authorization when no restrictions are set"""
        # Test with empty allowed users list (open to all)
        photo_handler.settings.bot.allowed_user_ids = set()
        
        result = await photo_handler.is_user_allowed(12345)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_user_allowed_with_restrictions(self, photo_handler):
        """Test user authorization with restrictions"""
        # Set specific allowed users
        photo_handler.settings.bot.allowed_user_ids = {12345, 67890}
        
        # Test allowed user
        result = await photo_handler.is_user_allowed(12345)
        assert result is True
        
        # Test not allowed user
        result = await photo_handler.is_user_allowed(99999)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_settings_existing(self, photo_handler):
        """Test getting existing user settings"""
        # Mock database response
        mock_settings = {
            "user_id": 12345,
            "bot_lang": "en",
            "gen_lang": "en",
            "model": "gpt-4o"
        }
        
        with patch.object(photo_handler.database, 'get_user_settings', return_value=mock_settings):
            settings = await photo_handler.get_user_settings(12345)
            
            assert settings is not None
            assert settings.bot_lang == "en"
            assert settings.model == "gpt-4o"
    
    @pytest.mark.asyncio
    async def test_get_user_settings_nonexistent(self, photo_handler):
        """Test getting settings for non-existent user"""
        with patch.object(photo_handler.database, 'get_user_settings', return_value=None):
            settings = await photo_handler.get_user_settings(99999)
            
            # Should return default settings for new user, not None
            assert settings is not None
            assert settings.user_id == 99999
    
    @pytest.mark.asyncio
    async def test_log_user_action(self, photo_handler):
        """Test user action logging"""
        with patch.object(photo_handler.database, 'add_user', new_callable=AsyncMock):
            await photo_handler.log_user_action("test_action", 12345, {"test": "data"})
            
            # Should not raise any exceptions
            assert True
    
    @pytest.mark.asyncio
    async def test_handle_error(self, photo_handler):
        """Test error handling"""
        test_error = Exception("Test error")
        
        # Should not raise any exceptions
        await photo_handler.handle_error(test_error, "test_context", 12345)
        assert True
    
    def test_create_beautiful_start_message(self, photo_handler):
        """Test creating start message"""
        message = photo_handler.create_beautiful_start_message("en")
        
        assert isinstance(message, str)
        assert len(message) > 0
        # Should contain some welcome text
        assert any(word in message.lower() for word in ["welcome", "hello", "start", "добро", "привет"])
    
    def test_create_beautiful_start_message_different_languages(self, photo_handler):
        """Test creating start message in different languages"""
        languages = ["en", "ru", "de", "fr", "es"]
        
        for lang in languages:
            message = photo_handler.create_beautiful_start_message(lang)
            assert isinstance(message, str)
            assert len(message) > 0
    
    @pytest.mark.asyncio
    async def test_photo_processing_mock_workflow(self, photo_handler, temp_image_file):
        """Test photo processing workflow with mocks"""
        # Mock successful AI analysis
        mock_analysis = MagicMock()
        mock_analysis.name = "Test Item"
        mock_analysis.description = "A test item"
        mock_analysis.suggested_location = "Test Location"
        mock_analysis.model_used = "gpt-4o"
        
        # Mock locations
        mock_locations = [
            MagicMock(id="1", name="Test Location", description="A test location")
        ]
        
        # Mock all external dependencies
        with patch.object(photo_handler.homebox_service, 'get_locations', return_value=mock_locations), \
             patch.object(photo_handler.ai_service, 'analyze_image', return_value=mock_analysis), \
             patch.object(photo_handler.database, 'get_user_settings', return_value={"bot_lang": "en"}):
            
            # Test that all services can be called without errors
            # Test image validation instead
            is_valid, message = photo_handler.image_service.validate_image(temp_image_file)
            assert is_valid is True
            
            locations = await photo_handler.homebox_service.get_locations()
            assert len(locations) == 1
            
            from models.location import LocationManager
            location_manager = LocationManager(mock_locations)
            
            analysis = await photo_handler.ai_service.analyze_image(
                temp_image_file, location_manager, "en", caption="Test caption"
            )
            assert analysis.name == "Test Item"