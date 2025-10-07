"""
Simple JSON-based database for storing user settings and bot data
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import aiofiles

logger = logging.getLogger(__name__)

class SimpleDatabase:
    def __init__(self, db_file: str = "bot_data.json"):
        self.db_file = db_file
        self._lock = asyncio.Lock()
        self._cache = {}
        self._load_data()
    
    def _load_data(self):
        """Загружает данные из файла"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded database from {self.db_file}")
            else:
                self._cache = {
                    'user_settings': {},
                    'bot_stats': {
                        'start_time': datetime.now().isoformat(),
                        'items_processed': 0,
                        'users_registered': [],
                        'total_requests': 0
                    }
                }
                self._save_data()
                logger.info(f"Created new database at {self.db_file}")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            self._cache = {
                'user_settings': {},
                'bot_stats': {
                    'start_time': datetime.now().isoformat(),
                    'items_processed': 0,
                    'users_registered': [],
                    'total_requests': 0
                }
            }
    
    async def _save_data(self):
        """Сохраняет данные в файл"""
        async with self._lock:
            try:
                async with aiofiles.open(self.db_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(self._cache, ensure_ascii=False, indent=2))
                logger.debug("Database saved successfully")
            except Exception as e:
                logger.error(f"Error saving database: {e}")
    
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Получает настройки пользователя"""
        return self._cache.get('user_settings', {}).get(str(user_id), {
            'lang': 'ru',
            'model': 'gpt-4o'
        })
    
    async def set_user_settings(self, user_id: int, settings: Dict[str, Any]):
        """Сохраняет настройки пользователя"""
        if 'user_settings' not in self._cache:
            self._cache['user_settings'] = {}
        
        self._cache['user_settings'][str(user_id)] = settings
        await self._save_data()
        logger.debug(f"Updated settings for user {user_id}")
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Получает статистику бота"""
        return self._cache.get('bot_stats', {})
    
    async def update_bot_stats(self, updates: Dict[str, Any]):
        """Обновляет статистику бота"""
        if 'bot_stats' not in self._cache:
            self._cache['bot_stats'] = {}
        
        self._cache['bot_stats'].update(updates)
        await self._save_data()
        logger.debug("Updated bot statistics")
    
    async def add_user(self, user_id: int):
        """Добавляет пользователя в список зарегистрированных"""
        stats = self._cache.get('bot_stats', {})
        users = set(stats.get('users_registered', []))
        users.add(user_id)
        stats['users_registered'] = list(users)
        await self.update_bot_stats(stats)
    
    async def increment_requests(self):
        """Увеличивает счетчик запросов"""
        stats = await self.get_bot_stats()
        await self.update_bot_stats({
            **stats,
            'total_requests': stats.get('total_requests', 0) + 1
        })
    
    async def increment_items_processed(self):
        """Увеличивает счетчик обработанных предметов"""
        stats = await self.get_bot_stats()
        await self.update_bot_stats({
            **stats,
            'items_processed': stats.get('items_processed', 0) + 1
        })
    
    async def cleanup_old_data(self, days: int = 30):
        """Очищает старые данные (не используется в текущей реализации)"""
        # Здесь можно добавить логику очистки старых данных
        pass

# Глобальный экземпляр базы данных
db = SimpleDatabase()
