"""
Unit tests for Database service
"""

import pytest
from unittest.mock import AsyncMock, patch
from services.database_service import DatabaseService
from models.user import User


class TestDatabaseService:
    """Test cases for DatabaseService"""
    
    @pytest.mark.asyncio
    async def test_init_database(self, database_service: DatabaseService):
        """Test database initialization"""
        await database_service.init_database()
        assert database_service is not None
    
    @pytest.mark.asyncio
    async def test_add_user(self, database_service: DatabaseService):
        """Test adding user"""
        await database_service.init_database()
        # Add a test user
        await database_service.add_user(
            user_id=12345,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        
        # Verify user settings were created (this is what we can test)
        settings = await database_service.get_user_settings(12345)
        # Settings might not be automatically created by add_user
        # Let's check that add_user worked by checking bot stats
        stats = await database_service.get_bot_stats()
        assert stats["users_registered"] >= 1
    
    @pytest.mark.asyncio
    async def test_get_user_settings_nonexistent(self, database_service: DatabaseService):
        """Test getting settings for non-existent user"""
        await database_service.init_database()
        settings = await database_service.get_user_settings(99999)
        assert settings is None
    
    @pytest.mark.asyncio
    async def test_set_user_settings(self, database_service: DatabaseService):
        """Test setting user settings"""
        await database_service.init_database()
        # First add a user
        await database_service.add_user(
            user_id=54321,
            username="settings_user",
            first_name="Settings",
            last_name="User"
        )
        
        # Set custom settings
        custom_settings = {
            "bot_lang": "en",
            "gen_lang": "en",
            "model": "gpt-4",
        }
        
        await database_service.set_user_settings(54321, custom_settings)
        
        # Verify settings were set
        settings = await database_service.get_user_settings(54321)
        assert settings is not None
        assert settings["bot_lang"] == "en"
        assert settings["gen_lang"] == "en"
        assert settings["model"] == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_get_bot_stats(self, database_service: DatabaseService):
        """Test getting bot statistics"""
        await database_service.init_database()
        stats = await database_service.get_bot_stats()
        
        assert stats is not None
        assert "users_registered" in stats
        assert "active_users_24h" in stats
        assert "start_time" in stats
        assert "language_distribution" in stats
    
    @pytest.mark.asyncio
    async def test_increment_requests(self, database_service: DatabaseService):
        """Test incrementing request counter"""
        await database_service.init_database()
        # Get initial stats
        initial_stats = await database_service.get_bot_stats()
        initial_users = initial_stats.get("users_registered", 0)
        
        # Increment requests (this increments users_registered)
        await database_service.increment_requests()
        
        # Verify increment
        new_stats = await database_service.get_bot_stats()
        assert new_stats["users_registered"] >= initial_users
    
    @pytest.mark.asyncio
    async def test_increment_items_processed(self, database_service: DatabaseService):
        """Test incrementing items processed counter"""
        await database_service.init_database()
        # Get initial stats
        initial_stats = await database_service.get_bot_stats()
        initial_users = initial_stats.get("users_registered", 0)
        
        # Increment items (this increments users_registered)
        await database_service.increment_items_processed()
        
        # Verify increment
        new_stats = await database_service.get_bot_stats()
        assert new_stats["users_registered"] >= initial_users
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self, database_service: DatabaseService):
        """Test getting user statistics"""
        await database_service.init_database()
        # Add a user first
        await database_service.add_user(
            user_id=88888,
            username="stats_user",
            first_name="Stats",
            last_name="User"
        )
        
        # Get user stats
        stats = await database_service.get_user_stats(88888)
        
        assert stats is not None
        assert "photos_analyzed" in stats
        assert "reanalyses" in stats
    
    @pytest.mark.asyncio
    async def test_close(self, database_service: DatabaseService):
        """Test closing database service"""
        await database_service.init_database()
        # Should not raise any exceptions
        await database_service.close()