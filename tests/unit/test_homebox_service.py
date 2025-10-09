"""
Unit tests for HomeBox service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.homebox_service import HomeBoxService
from models.location import Location, LocationManager
from models.item import Item


class TestHomeBoxService:
    """Test cases for HomeBoxService"""
    
    def test_build_auth_header_with_token(self, homebox_service: HomeBoxService):
        """Test building auth header with token"""
        header = homebox_service._build_auth_header("test_token")
        assert header == "Bearer test_token"
        
        header = homebox_service._build_auth_header("Bearer test_token")
        assert header == "Bearer test_token"
    
    def test_build_auth_header_without_token(self, homebox_service: HomeBoxService):
        """Test building auth header without token"""
        header = homebox_service._build_auth_header(None)
        assert header == ""
    
    @pytest.mark.asyncio
    async def test_initialize_with_token(self, homebox_service: HomeBoxService):
        """Test initialization with existing token"""
        # Provide a pre-existing token to avoid login
        homebox_service.token = "test_homebox_token"
        with patch.object(homebox_service, '_get_session', new_callable=AsyncMock) as mock_session, \
             patch.object(homebox_service, '_login', new_callable=AsyncMock) as mock_login:
            await homebox_service.initialize()
            mock_session.assert_called_once()
            mock_login.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_initialize_with_login(self, homebox_service: HomeBoxService):
        """Test initialization with username/password login"""
        # Remove token to force login
        homebox_service.token = None
        
        with patch.object(homebox_service, '_get_session', new_callable=AsyncMock) as mock_session, \
             patch.object(homebox_service, '_login', new_callable=AsyncMock) as mock_login:
            
            await homebox_service.initialize()
            
            mock_session.assert_called_once()
            mock_login.assert_called_once()
    
    def test_get_location_manager(self, homebox_service: HomeBoxService):
        """Test creating location manager with filtering"""
        locations = [
            Location(id="1", name="Kitchen", description="Food storage [TGB]"),
            Location(id="2", name="Garage", description="Car storage"),
            Location(id="3", name="Bedroom", description="Sleep area [TGB]")
        ]
        
        # Test marker filtering
        location_manager = homebox_service.get_location_manager(locations)
        
        assert len(location_manager.locations) == 3
        # Check that marker filtering is applied
        for loc in location_manager.locations:
            if "[TGB]" in loc.description:
                assert loc.is_allowed is True
            else:
                assert loc.is_allowed is False
    
    def test_get_location_manager_all_mode(self, homebox_service: HomeBoxService):
        """Test location manager in 'all' mode"""
        # Change filter mode to 'all'
        homebox_service.settings.location_filter_mode = 'all'
        
        locations = [
            Location(id="1", name="Kitchen", description="Food storage"),
            Location(id="2", name="Garage", description="Car storage")
        ]
        
        location_manager = homebox_service.get_location_manager(locations)
        
        assert len(location_manager.locations) == 2
        # In 'all' mode, all locations should be allowed
        for loc in location_manager.locations:
            assert loc.is_allowed is True
    
    def test_get_location_manager_none_mode(self, homebox_service: HomeBoxService):
        """Test location manager in 'none' mode"""
        # Change filter mode to 'none'
        homebox_service.settings.location_filter_mode = 'none'
        
        locations = [
            Location(id="1", name="Kitchen [TGB]", description="Food storage"),
            Location(id="2", name="Garage", description="Car storage")
        ]
        
        location_manager = homebox_service.get_location_manager(locations)
        
        assert len(location_manager.locations) == 2
        # In 'none' mode, no locations should be allowed
        for loc in location_manager.locations:
            assert loc.is_allowed is False
    
    @pytest.mark.asyncio
    async def test_search_items_empty_query(self, homebox_service: HomeBoxService):
        """Test item search with empty query"""
        items = await homebox_service.search_items("")
        assert items == []
    
    @pytest.mark.asyncio
    async def test_close_session(self, homebox_service: HomeBoxService):
        """Test closing HTTP session"""
        # Mock session and lock
        mock_session = AsyncMock()
        mock_session.closed = False
        homebox_service._session = mock_session
        
        # Mock the session lock
        with patch.object(homebox_service, '_session_lock'):
            await homebox_service.close()
        
        mock_session.close.assert_called_once()
        assert homebox_service._session is None
    
    def test_item_creation_data_structure(self, homebox_service: HomeBoxService):
        """Test that Item model works correctly with HomeBox service"""
        test_item = Item(
            name="Test Item",
            description="A test item for testing",
            location_id="1",
            location_name="Test Location"
        )
        
        # Test item conversion to dict
        item_dict = test_item.to_dict()
        assert item_dict["name"] == "Test Item"
        assert item_dict["description"] == "A test item for testing"
        assert item_dict["locationId"] == "1"
        assert item_dict["quantity"] == 1
        
        # Test HomeBox format conversion
        homebox_dict = test_item.to_homebox_format()
        assert homebox_dict["name"] == "Test Item"
        assert homebox_dict["locationId"] == "1"
    
    def test_location_model_integration(self, homebox_service: HomeBoxService):
        """Test Location model integration"""
        location = Location(
            id="1",
            name="Test Location",
            description="A test location"
        )
        
        # Test that location can be used in location manager
        location_manager = LocationManager([location])
        assert len(location_manager.locations) == 1
        assert location_manager.locations[0].name == "Test Location"
        
        # Test location filtering
        location.is_allowed = True
        assert location.is_allowed is True
        
        location.is_allowed = False
        assert location.is_allowed is False
    
    def test_service_initialization(self, homebox_service: HomeBoxService):
        """Test that service initializes correctly"""
        assert homebox_service.base_url == "http://localhost:7745"
        # Token is obtained on login; not provided via settings anymore
        assert homebox_service.token is None
        assert homebox_service.settings is not None
        assert homebox_service.settings.location_filter_mode == "marker"
        assert homebox_service.settings.location_marker == "[TGB]"
    
    @pytest.mark.asyncio
    async def test_error_handling_structure(self, homebox_service: HomeBoxService):
        """Test error handling structure"""
        # Test that last_error is initially None
        assert homebox_service.last_error is None
        
        # Test that we can set an error
        homebox_service.last_error = "Test error"
        assert homebox_service.last_error == "Test error"
        
        # Test that we can clear an error
        homebox_service.last_error = None
        assert homebox_service.last_error is None