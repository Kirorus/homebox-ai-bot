"""
Unit tests for AI service
"""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from services.ai_service import AIService
from models.item import ItemAnalysis
from models.location import Location, LocationManager


class TestAIService:
    """Test cases for AIService"""
    
    def test_encode_image(self, ai_service: AIService, temp_image_file: str):
        """Test image encoding to base64"""
        encoded = ai_service.encode_image(temp_image_file)
        
        # Verify it's valid base64
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0
        assert decoded.startswith(b'\xff\xd8')  # JPEG header
    
    def test_build_locations_text(self, ai_service: AIService):
        """Test building locations text for AI prompt"""
        locations = [
            Location(id=1, name="Kitchen", description="Where food is stored"),
            Location(id=2, name="Garage", description=None),
            Location(id=3, name="Bedroom", description="Personal items storage")
        ]
        location_manager = LocationManager(locations)
        
        text = ai_service._build_locations_text(location_manager)
        
        assert "Kitchen: Where food is stored" in text
        assert "- Garage" in text
        assert "Bedroom: Personal items storage" in text
    
    def test_build_prompt_without_caption(self, ai_service: AIService):
        """Test building AI prompt without caption"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        prompt = ai_service._build_prompt(location_manager, "en")
        
        assert "Kitchen: Food storage" in prompt
        assert "JSON" in prompt
    
    def test_build_prompt_with_caption(self, ai_service: AIService):
        """Test building AI prompt with caption"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        prompt = ai_service._build_prompt(location_manager, "ru", "This is a test item")
        
        assert "Kitchen: Food storage" in prompt
        assert "This is a test item" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_image_success(self, ai_service: AIService, temp_image_file: str):
        """Test successful image analysis"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        # Create proper mock response object
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"name": "Apple", "description": "A red apple", "suggested_location": "Kitchen"}'
        
        with patch.object(ai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await ai_service.analyze_image(temp_image_file, location_manager, "en")
            
            assert result is not None
            assert result.name == "Apple"
            assert result.description == "A red apple"
            assert result.suggested_location == "Kitchen"
            
            # Verify the API was called with correct parameters
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            
            assert call_args[1]["model"] == ai_service.settings.default_model
            assert len(call_args[1]["messages"]) == 1
            assert call_args[1]["messages"][0]["role"] == "user"
            assert "content" in call_args[1]["messages"][0]
            assert "image_url" in call_args[1]["messages"][0]["content"][1]
    
    @pytest.mark.asyncio
    async def test_analyze_image_api_error(self, ai_service: AIService, temp_image_file: str):
        """Test image analysis with API error"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        with patch.object(ai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = await ai_service.analyze_image(temp_image_file, location_manager, "en")
            
            # Should return error analysis, not None
            assert result is not None
            assert "Unknown item" in result.name or "Неизвестный предмет" in result.name
    
    @pytest.mark.asyncio
    async def test_analyze_image_invalid_json(self, ai_service: AIService, temp_image_file: str):
        """Test image analysis with invalid JSON response"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        # Create proper mock response object
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        
        with patch.object(ai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await ai_service.analyze_image(temp_image_file, location_manager, "en")
            
            # Should return error analysis, not None
            assert result is not None
            assert "Unknown item" in result.name or "Failed to parse" in result.description
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_custom_model(self, ai_service: AIService, temp_image_file: str):
        """Test image analysis with custom model"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        # Create proper mock response object
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"name": "Apple", "description": "A red apple", "suggested_location": "Kitchen"}'
        
        with patch.object(ai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await ai_service.analyze_image(temp_image_file, location_manager, "en", model="gpt-4-turbo")
            
            assert result is not None
            assert result.model_used == "gpt-4-turbo"
            
            # Verify the API was called with custom model
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["model"] == "gpt-4-turbo"
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_caption(self, ai_service: AIService, temp_image_file: str):
        """Test image analysis with caption"""
        locations = [Location(id=1, name="Kitchen", description="Food storage")]
        location_manager = LocationManager(locations)
        
        # Create proper mock response object
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"name": "Apple", "description": "A red apple", "suggested_location": "Kitchen"}'
        
        with patch.object(ai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await ai_service.analyze_image(
                temp_image_file, 
                location_manager, 
                "en", 
                caption="This is a red apple"
            )
            
            assert result is not None
            assert result.name == "Apple"
            
            # Verify the prompt was built with caption
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            prompt = call_args[1]["messages"][0]["content"][0]["text"]
            assert "This is a red apple" in prompt