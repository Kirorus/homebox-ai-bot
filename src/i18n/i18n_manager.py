"""
I18n Manager for handling translations
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class I18nManager:
    """Manages internationalization and translations"""
    
    def __init__(self, locales_dir: str = None):
        """
        Initialize I18nManager
        
        Args:
            locales_dir: Path to locales directory
        """
        if locales_dir is None:
            # Get the directory where this file is located
            current_dir = Path(__file__).parent
            locales_dir = current_dir / "locales"
        
        self.locales_dir = Path(locales_dir)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.default_language = "en"
        self.supported_languages = ["en", "ru", "de", "fr", "es"]
        
        # Load all translations
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files"""
        try:
            for lang in self.supported_languages:
                lang_file = self.locales_dir / f"{lang}.json"
                if lang_file.exists():
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang] = json.load(f)
                    logger.info(f"Loaded translations for language: {lang}")
                else:
                    logger.warning(f"Translation file not found for language: {lang}")
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
    
    def get_text(self, language: str, key: str, **kwargs) -> str:
        """
        Get translated text for a given language and key
        
        Args:
            language: Language code (e.g., 'en', 'ru', 'de')
            key: Translation key (e.g., 'settings.title', 'item.name')
            **kwargs: Format parameters for string formatting
            
        Returns:
            Translated text or key if translation not found
        """
        try:
            # Normalize language code
            language = language.lower()
            
            # Check if language is supported
            if language not in self.supported_languages:
                language = self.default_language
            
            # Get translation
            translation = self.translations.get(language, {})
            
            # Navigate through nested keys (e.g., 'settings.title' -> translation['settings']['title'])
            keys = key.split('.')
            for k in keys:
                if isinstance(translation, dict) and k in translation:
                    translation = translation[k]
                else:
                    # Fallback to default language
                    if language != self.default_language:
                        return self.get_text(self.default_language, key, **kwargs)
                    # If still not found, return the key
                    logger.warning(f"Translation key not found: {key} for language: {language}")
                    return key
            
            # Format string if kwargs provided
            if kwargs and isinstance(translation, str):
                try:
                    return translation.format(**kwargs)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error formatting translation for key {key}: {e}")
                    return translation
            
            return str(translation) if translation is not None else key
            
        except Exception as e:
            logger.error(f"Error getting translation for key {key}: {e}")
            return key
    
    def get_available_languages(self) -> list:
        """Get list of available languages"""
        return list(self.translations.keys())
    
    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported"""
        return language.lower() in self.supported_languages
    
    def reload_translations(self):
        """Reload all translation files"""
        self.translations.clear()
        self._load_translations()
    
    def get_language_name(self, language: str, display_language: str = None) -> str:
        """
        Get display name for a language
        
        Args:
            language: Language code to get name for
            display_language: Language to display the name in (defaults to the same language)
        
        Returns:
            Display name of the language
        """
        if display_language is None:
            display_language = language
        
        return self.get_text(display_language, f"languages.{language}")


# Global instance
i18n_manager = I18nManager()


def t(language: str, key: str, **kwargs) -> str:
    """
    Convenience function to get translated text
    
    Args:
        language: Language code
        key: Translation key
        **kwargs: Format parameters
        
    Returns:
        Translated text
    """
    return i18n_manager.get_text(language, key, **kwargs)


def get_language_name(language: str, display_language: str = None) -> str:
    """
    Convenience function to get language display name
    
    Args:
        language: Language code
        display_language: Language to display the name in
        
    Returns:
        Language display name
    """
    return i18n_manager.get_language_name(language, display_language)
