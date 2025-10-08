"""
Item-related data models
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class ItemAnalysis:
    """AI analysis result for an item"""
    name: str
    description: str
    suggested_location: str
    confidence: Optional[float] = None
    model_used: Optional[str] = None
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        # Validate name length
        if len(self.name) > 50:
            self.name = self.name[:47] + "..."
        
        # Validate description length
        if len(self.description) > 200:
            self.description = self.description[:197] + "..."


@dataclass
class Item:
    """Item data model"""
    name: str
    description: str
    location_id: str
    location_name: str
    photo_path: Optional[str] = None
    photo_file_id: Optional[str] = None
    created_at: Optional[datetime] = None
    homebox_id: Optional[str] = None
    analysis: Optional[ItemAnalysis] = None
    
    def __post_init__(self):
        # Validate required fields
        if not self.name or not self.name.strip():
            raise ValueError("Item name cannot be empty")
        
        if not self.description or not self.description.strip():
            raise ValueError("Item description cannot be empty")
        
        if not self.location_id or not self.location_id.strip():
            raise ValueError("Location ID cannot be empty")
        
        # Clean up strings
        self.name = self.name.strip()
        self.description = self.description.strip()
        self.location_id = str(self.location_id).strip()
        
        # Set creation time if not provided
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {
            'name': self.name,
            'description': self.description,
            'locationId': self.location_id,
            'quantity': 1
        }
    
    def to_homebox_format(self) -> Dict[str, Any]:
        """Convert to HomeBox API format"""
        return {
            'name': self.name,
            'description': self.description,
            'locationId': self.location_id,
            'quantity': 1
        }
