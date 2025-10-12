"""
Database service for SQLite operations
"""

import aiosqlite
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for SQLite operations"""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        # Ensure directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Database will be created at: {self.db_path}")
    
    async def init_database(self):
        """Initialize database tables"""
        try:
            logger.info(f"Initializing database at: {self.db_path}")
            async with aiosqlite.connect(self.db_path) as db:
                # Users table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TEXT,
                        last_activity TEXT
                    )
                """)
                
                # User settings table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id INTEGER PRIMARY KEY,
                        bot_lang TEXT DEFAULT 'ru',
                        gen_lang TEXT DEFAULT 'ru',
                        model TEXT DEFAULT 'gpt-4o',
                        created_at TEXT,
                        last_activity TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Bot stats table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS bot_stats (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT
                    )
                """)
                
                # Initialize bot stats if empty
                await db.execute("""
                    INSERT OR IGNORE INTO bot_stats (key, value, updated_at) 
                    VALUES ('start_time', ?, ?)
                """, (datetime.now().isoformat(), datetime.now().isoformat()))
                
                await db.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.error(f"Database path: {self.db_path}")
            raise
    
    async def close(self):
        """Close database connections"""
        # SQLite connections are closed automatically
        pass
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_activity)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, datetime.now().isoformat()))
            await db.commit()
    
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user settings"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM user_settings WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def set_user_settings(self, user_id: int, settings: Dict[str, Any]):
        """Set user settings"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_settings 
                (user_id, bot_lang, gen_lang, model, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                settings.get('bot_lang', 'ru'),
                settings.get('gen_lang', 'ru'),
                settings.get('model', 'gpt-4o'),
                settings.get('created_at', datetime.now().isoformat()),
                settings.get('last_activity', datetime.now().isoformat())
            ))
            await db.commit()
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            async with db.execute("SELECT key, value FROM bot_stats") as cursor:
                async for row in cursor:
                    stats[row[0]] = row[1]
            
            # Add counts
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                stats['users_registered'] = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM user_settings") as cursor:
                stats['user_settings'] = (await cursor.fetchone())[0]
            
            # Add user activity stats
            async with db.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_activity > datetime('now', '-24 hours')
            """) as cursor:
                stats['active_users_24h'] = (await cursor.fetchone())[0]
            
            async with db.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_activity > datetime('now', '-7 days')
            """) as cursor:
                stats['active_users_7d'] = (await cursor.fetchone())[0]
            
            # Add language distribution
            async with db.execute("""
                SELECT bot_lang, COUNT(*) FROM user_settings 
                GROUP BY bot_lang ORDER BY COUNT(*) DESC
            """) as cursor:
                stats['language_distribution'] = dict(await cursor.fetchall())
            
            # Add model distribution
            async with db.execute("""
                SELECT model, COUNT(*) FROM user_settings 
                GROUP BY model ORDER BY COUNT(*) DESC
            """) as cursor:
                stats['model_distribution'] = dict(await cursor.fetchall())
            
            return stats
    
    async def increment_requests(self):
        """Increment request counter"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO bot_stats (key, value, updated_at)
                VALUES ('total_requests', 
                       COALESCE((SELECT CAST(value AS INTEGER) FROM bot_stats WHERE key = 'total_requests'), 0) + 1,
                       ?)
            """, (datetime.now().isoformat(),))
            await db.commit()
    
    async def increment_items_processed(self):
        """Increment items processed counter"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO bot_stats (key, value, updated_at)
                VALUES ('items_processed', 
                       COALESCE((SELECT CAST(value AS INTEGER) FROM bot_stats WHERE key = 'items_processed'), 0) + 1,
                       ?)
            """, (datetime.now().isoformat(),))
            await db.commit()
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user-specific statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Get user info
            async with db.execute("""
                SELECT username, first_name, last_name, created_at, last_activity 
                FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                user_row = await cursor.fetchone()
                if user_row:
                    stats['username'] = user_row[0]
                    stats['first_name'] = user_row[1]
                    stats['last_name'] = user_row[2]
                    stats['account_created'] = user_row[3]
                    stats['last_activity'] = user_row[4]
            
            # Get user settings
            async with db.execute("""
                SELECT bot_lang, gen_lang, model, created_at, last_activity 
                FROM user_settings WHERE user_id = ?
            """, (user_id,)) as cursor:
                settings_row = await cursor.fetchone()
                if settings_row:
                    stats['bot_lang'] = settings_row[0]
                    stats['gen_lang'] = settings_row[1]
                    stats['model'] = settings_row[2]
                    stats['settings_created'] = settings_row[3]
                    stats['settings_updated'] = settings_row[4]
            
            # Count user's photos analyzed (approximate from requests)
            async with db.execute("""
                SELECT COUNT(*) FROM bot_stats 
                WHERE key LIKE 'user_%_photos' AND key LIKE ? 
            """, (f'user_{user_id}_%',)) as cursor:
                stats['photos_analyzed'] = (await cursor.fetchone())[0]
            
            # Count user's reanalyses (approximate from requests)
            async with db.execute("""
                SELECT COUNT(*) FROM bot_stats 
                WHERE key LIKE 'user_%_reanalyses' AND key LIKE ? 
            """, (f'user_{user_id}_%',)) as cursor:
                stats['reanalyses'] = (await cursor.fetchone())[0]
            
            return stats
