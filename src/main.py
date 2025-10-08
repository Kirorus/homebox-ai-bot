"""
Main application entry point
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from services.database_service import DatabaseService
from services.homebox_service import HomeBoxService
from services.ai_service import AIService
from services.image_service import ImageService
from bot.handlers import register_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class HomeBoxAIBot:
    """Main bot application class"""
    
    def __init__(self):
        self.settings = load_settings()
        self.bot = Bot(token=self.settings.bot.token)
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Initialize services
        self.database = DatabaseService("../bot_data.db")  # Database in parent directory
        self.homebox_service = HomeBoxService(self.settings.homebox)
        self.ai_service = AIService(self.settings.ai)
        self.image_service = ImageService()
        
        # Register handlers
        register_handlers(self.dp, self.settings, self.database, self.homebox_service, self.ai_service, self.image_service, self.bot)
    
    async def start(self):
        """Start the bot"""
        try:
            # Initialize database
            await self.database.init_database()
            logger.info("Database initialized")
            
            # Initialize HomeBox service
            await self.homebox_service.initialize()
            logger.info("HomeBox service initialized")
            
            # Start polling
            logger.info("Starting bot...")
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.homebox_service.close()
            await self.database.close()
            await self.bot.session.close()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point"""
    bot = HomeBoxAIBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
