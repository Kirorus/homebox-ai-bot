"""
User-related data models
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class UserSettings:
    """User settings and preferences"""
    user_id: int
    bot_lang: str = 'ru'
    gen_lang: str = 'ru'
    model: str = 'gpt-4o'
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def __post_init__(self):
        # Validate language codes
        if self.bot_lang not in ['ru', 'en', 'de', 'fr', 'es']:
            self.bot_lang = 'ru'
        
        if self.gen_lang not in ['ru', 'en', 'de', 'fr', 'es']:
            self.gen_lang = 'ru'
        
        # Set timestamps if not provided
        if self.created_at is None:
            self.created_at = datetime.now()
        
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'user_id': self.user_id,
            'bot_lang': self.bot_lang,
            'gen_lang': self.gen_lang,
            'model': self.model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            bot_lang=data.get('bot_lang', 'ru'),
            gen_lang=data.get('gen_lang', 'ru'),
            model=data.get('model', 'gpt-4o'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            last_activity=datetime.fromisoformat(data['last_activity']) if data.get('last_activity') else None
        )


@dataclass
class User:
    """User data model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    settings: Optional[UserSettings] = None
    
    def __post_init__(self):
        # Set timestamps if not provided
        if self.created_at is None:
            self.created_at = datetime.now()
        
        if self.last_activity is None:
            self.last_activity = datetime.now()
        
        # Create default settings if not provided
        if self.settings is None:
            self.settings = UserSettings(user_id=self.user_id)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        if self.settings:
            self.settings.last_activity = self.last_activity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'settings': self.settings.to_dict() if self.settings else None
        }
