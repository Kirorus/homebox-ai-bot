"""
Configuration loading utilities
"""

import logging
from typing import Optional
from .settings import Settings

logger = logging.getLogger(__name__)

# Global settings instance
_settings: Optional[Settings] = None


def load_settings() -> Settings:
    """Load and return application settings"""
    global _settings
    
    if _settings is None:
        try:
            _settings = Settings.from_env()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    return _settings


def get_settings() -> Settings:
    """Get current settings instance"""
    if _settings is None:
        return load_settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = None
    return load_settings()
