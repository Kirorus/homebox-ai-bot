"""
Pytest configuration and fixtures
"""

import asyncio
import pytest
import tempfile
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator, Generator

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import Settings, BotSettings, AISettings, HomeBoxSettings
from services.database_service import DatabaseService
from services.ai_service import AIService
from services.homebox_service import HomeBoxService
from services.image_service import ImageService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_db() -> AsyncGenerator[str, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        bot=BotSettings(
            token="test_token",
            allowed_user_ids=[]
        ),
        ai=AISettings(
            api_key="test_openai_key",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4o"
        ),
        homebox=HomeBoxSettings(
            url="http://localhost:7745",
            # token removed; login uses username/password
            username="test_user",
            password="test_pass"
        )
    )


@pytest.fixture
def database_service(temp_db: str) -> DatabaseService:
    """Create database service for testing."""
    service = DatabaseService(temp_db)
    return service


@pytest.fixture
def ai_service(test_settings: Settings) -> AIService:
    """Create AI service for testing."""
    return AIService(test_settings.ai)


@pytest.fixture
def homebox_service(test_settings: Settings) -> HomeBoxService:
    """Create HomeBox service for testing."""
    return HomeBoxService(test_settings.homebox)


@pytest.fixture
def image_service() -> ImageService:
    """Create image service for testing."""
    return ImageService()


@pytest.fixture
def mock_telegram_bot() -> MagicMock:
    """Create mock Telegram bot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_document = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.edit_message_media = AsyncMock()
    return bot


@pytest.fixture
def mock_telegram_message() -> MagicMock:
    """Create mock Telegram message."""
    message = MagicMock()
    message.message_id = 123
    message.chat.id = 456789
    message.from_user.id = 456789
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.photo = None
    message.caption = None
    message.text = None
    return message


@pytest.fixture
def mock_telegram_callback_query() -> MagicMock:
    """Create mock Telegram callback query."""
    query = MagicMock()
    query.id = "test_query_id"
    query.from_user.id = 456789
    query.data = "test_callback_data"
    query.message = mock_telegram_message()
    return query


@pytest.fixture
def mock_ai_response() -> dict:
    """Create mock AI response."""
    return {
        "name": "Test Item",
        "description": "A test item for testing purposes",
        "location": "Test Location",
        "confidence": 0.95
    }


@pytest.fixture
def mock_homebox_locations() -> list:
    """Create mock HomeBox locations."""
    return [
        {
            "id": 1,
            "name": "Test Location 1",
            "description": "A test location"
        },
        {
            "id": 2,
            "name": "Test Location 2",
            "description": "Another test location"
        }
    ]


@pytest.fixture
def mock_homebox_items() -> list:
    """Create mock HomeBox items."""
    return [
        {
            "id": 1,
            "name": "Existing Item 1",
            "description": "An existing test item",
            "location": {"name": "Test Location 1"},
            "attachments": []
        },
        {
            "id": 2,
            "name": "Existing Item 2",
            "description": "Another existing test item",
            "location": {"name": "Test Location 2"},
            "attachments": []
        }
    ]


@pytest.fixture
def temp_image_file() -> Generator[str, None, None]:
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        # Create a minimal valid JPEG file
        tmp.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xff\xd9')
        tmp.flush()
        yield tmp.name
    
    # Cleanup
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture(scope="session", autouse=True)
def cleanup_stray_test_artifacts() -> Generator[None, None, None]:
    """Automatically remove stray files created during tests.

    Historically, some tests or fixtures could accidentally create files with
    names like "<async_generator object temp_db at 0x...>" in the repository
    root. This fixture ensures such artifacts are cleaned up after the test
    session finishes, keeping the workspace tidy and preventing accidental
    commits of these files.
    """
    yield

    cwd = Path.cwd()
    for entry in cwd.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        # Remove files that look like leaked async generator reprs from fixtures
        if name.startswith("<async_generator object temp_db"):
            try:
                entry.unlink()
            except Exception:
                # Best-effort cleanup; ignore failures
                pass
