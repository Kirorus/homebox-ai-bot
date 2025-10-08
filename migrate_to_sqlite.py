#!/usr/bin/env python3
"""
Migration script to convert JSON database to SQLite
"""
import json
import os
import asyncio
import logging
from datetime import datetime
from database_sqlite import SQLiteDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_json_to_sqlite(json_file: str = "bot_data.json", sqlite_file: str = "bot_data.db"):
    """Migrate data from JSON to SQLite database"""
    
    # Check if JSON file exists
    if not os.path.exists(json_file):
        logger.warning(f"JSON file {json_file} not found. Creating new SQLite database.")
        db = SQLiteDatabase(sqlite_file)
        await db.init_database()
        return
    
    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        logger.info(f"Loaded JSON data from {json_file}")
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        return
    
    # Initialize SQLite database
    db = SQLiteDatabase(sqlite_file)
    await db.init_database()
    
    # Migrate user settings
    user_settings = json_data.get('user_settings', {})
    migrated_users = 0
    
    for user_id_str, settings in user_settings.items():
        try:
            user_id = int(user_id_str)
            await db.set_user_settings(user_id, settings)
            migrated_users += 1
            logger.debug(f"Migrated user {user_id}")
        except Exception as e:
            logger.error(f"Error migrating user {user_id_str}: {e}")
    
    # Migrate bot stats
    bot_stats = json_data.get('bot_stats', {})
    if bot_stats:
        try:
            await db.update_bot_stats(bot_stats)
            logger.info("Migrated bot statistics")
        except Exception as e:
            logger.error(f"Error migrating bot stats: {e}")
    
    # Migrate registered users
    users_registered = bot_stats.get('users_registered', [])
    migrated_registrations = 0
    
    for user_id in users_registered:
        try:
            await db.add_user(user_id)
            migrated_registrations += 1
        except Exception as e:
            logger.error(f"Error migrating user registration {user_id}: {e}")
    
    logger.info(f"Migration completed:")
    logger.info(f"  - Users migrated: {migrated_users}")
    logger.info(f"  - Registrations migrated: {migrated_registrations}")
    logger.info(f"  - Bot stats migrated: {'Yes' if bot_stats else 'No'}")
    
    # Verify migration
    await verify_migration(db, json_data)

async def verify_migration(db: SQLiteDatabase, original_data: dict):
    """Verify that migration was successful"""
    logger.info("Verifying migration...")
    
    # Check user settings
    original_users = original_data.get('user_settings', {})
    for user_id_str in original_users.keys():
        user_id = int(user_id_str)
        sqlite_settings = await db.get_user_settings(user_id)
        original_settings = original_users[user_id_str]
        
        # Compare settings (ignore timestamps)
        for key in ['bot_lang', 'gen_lang', 'model']:
            if sqlite_settings.get(key) != original_settings.get(key):
                logger.error(f"Settings mismatch for user {user_id}, key {key}")
                return False
    
    # Check bot stats
    original_stats = original_data.get('bot_stats', {})
    sqlite_stats = await db.get_bot_stats()
    
    for key in ['items_processed', 'total_requests']:
        if sqlite_stats.get(key) != original_stats.get(key):
            logger.error(f"Stats mismatch for key {key}")
            return False
    
    logger.info("✅ Migration verification successful!")
    return True

async def main():
    """Main migration function"""
    print("🔄 Starting JSON to SQLite migration...")
    print("=" * 40)
    
    # Check if SQLite file already exists
    if os.path.exists("bot_data.db"):
        response = input("SQLite database already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
    
    await migrate_json_to_sqlite()
    
    print("\n🎉 Migration completed!")
    print("You can now use the SQLite database.")
    print("\nTo switch to SQLite:")
    print("1. Update bot.py to import from database_sqlite")
    print("2. Test the bot")
    print("3. Remove old JSON file if everything works")

if __name__ == "__main__":
    asyncio.run(main())
