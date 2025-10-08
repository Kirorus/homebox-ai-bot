"""
SQLite-based database for storing user settings and bot data
"""
import sqlite3
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiosqlite

logger = logging.getLogger(__name__)

class SQLiteDatabase:
    def __init__(self, db_file: str = "bot_data.db"):
        self.db_file = db_file
        self._lock = asyncio.Lock()
    
    def _get_connection(self):
        """Get database connection"""
        return aiosqlite.connect(self.db_file)
    
    async def init_database(self):
        """Initialize database tables"""
        async with self._get_connection() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    bot_lang TEXT DEFAULT 'ru',
                    gen_lang TEXT DEFAULT 'ru',
                    model TEXT DEFAULT 'gpt-4o',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bot stats table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    items_processed INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    UNIQUE(id)
                )
            """)
            
            # User registrations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_registrations (
                    user_id INTEGER PRIMARY KEY,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize bot stats if not exists
            await conn.execute("""
                INSERT OR IGNORE INTO bot_stats (id, start_time, items_processed, total_requests)
                VALUES (1, ?, 0, 0)
            """, (datetime.now().isoformat(),))
            
            await conn.commit()
            logger.info("Database initialized successfully")
    
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT bot_lang, gen_lang, model, created_at, updated_at
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = await cursor.fetchone()
            if row:
                return {
                    'bot_lang': row[0],
                    'gen_lang': row[1],
                    'model': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                }
            else:
                # Return default settings
                return {
                    'bot_lang': 'ru',
                    'gen_lang': 'ru',
                    'model': 'gpt-4o'
                }
    
    async def set_user_settings(self, user_id: int, settings: Dict[str, Any]):
        """Save user settings"""
        async with self._lock:
            async with self._get_connection() as conn:
                # Check if user exists
                cursor = await conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                exists = await cursor.fetchone()
                
                if exists:
                    # Update existing user
                    await conn.execute("""
                        UPDATE users 
                        SET bot_lang = ?, gen_lang = ?, model = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        settings.get('bot_lang', 'ru'),
                        settings.get('gen_lang', 'ru'),
                        settings.get('model', 'gpt-4o'),
                        datetime.now().isoformat(),
                        user_id
                    ))
                else:
                    # Insert new user
                    await conn.execute("""
                        INSERT INTO users (id, bot_lang, gen_lang, model, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        settings.get('bot_lang', 'ru'),
                        settings.get('gen_lang', 'ru'),
                        settings.get('model', 'gpt-4o'),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                
                await conn.commit()
                logger.debug(f"Updated settings for user {user_id}")
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT start_time, items_processed, total_requests
                FROM bot_stats WHERE id = 1
            """)
            
            row = await cursor.fetchone()
            if row:
                # Get registered users count
                cursor = await conn.execute("SELECT COUNT(*) FROM user_registrations")
                users_count = (await cursor.fetchone())[0]
                
                return {
                    'start_time': row[0],
                    'items_processed': row[1],
                    'total_requests': row[2],
                    'users_registered': users_count
                }
            else:
                return {
                    'start_time': datetime.now().isoformat(),
                    'items_processed': 0,
                    'total_requests': 0,
                    'users_registered': 0
                }
    
    async def update_bot_stats(self, updates: Dict[str, Any]):
        """Update bot statistics"""
        async with self._lock:
            async with self._get_connection() as conn:
                # Build update query dynamically
                set_clauses = []
                values = []
                
                for key, value in updates.items():
                    if key in ['start_time', 'items_processed', 'total_requests']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if set_clauses:
                    values.append(1)  # WHERE id = 1
                    query = f"UPDATE bot_stats SET {', '.join(set_clauses)} WHERE id = ?"
                    await conn.execute(query, values)
                    await conn.commit()
                    logger.debug("Updated bot statistics")
    
    async def add_user(self, user_id: int):
        """Add user to registered users list"""
        async with self._lock:
            async with self._get_connection() as conn:
                await conn.execute("""
                    INSERT OR IGNORE INTO user_registrations (user_id, registered_at)
                    VALUES (?, ?)
                """, (user_id, datetime.now().isoformat()))
                await conn.commit()
                logger.debug(f"Added user {user_id} to registrations")
    
    async def increment_requests(self):
        """Increment request counter"""
        async with self._lock:
            async with self._get_connection() as conn:
                await conn.execute("""
                    UPDATE bot_stats 
                    SET total_requests = total_requests + 1 
                    WHERE id = 1
                """)
                await conn.commit()
                logger.debug("Incremented request counter")
    
    async def increment_items_processed(self):
        """Increment processed items counter"""
        async with self._lock:
            async with self._get_connection() as conn:
                await conn.execute("""
                    UPDATE bot_stats 
                    SET items_processed = items_processed + 1 
                    WHERE id = 1
                """)
                await conn.commit()
                logger.debug("Incremented items processed counter")
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users with their settings"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT id, bot_lang, gen_lang, model, created_at, updated_at
                FROM users ORDER BY created_at DESC
            """)
            
            rows = await cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'bot_lang': row[1],
                    'gen_lang': row[2],
                    'model': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                }
                for row in rows
            ]
    
    async def get_user_count(self) -> int:
        """Get total number of registered users"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM user_registrations")
            return (await cursor.fetchone())[0]
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old data (placeholder for future use)"""
        # This can be implemented later if needed
        pass
    
    async def close(self):
        """Close database connection"""
        # aiosqlite handles connection closing automatically
        pass

# Global database instance
db = SQLiteDatabase()
