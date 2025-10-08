"""
Location-related data models
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class Location:
    """Location data model"""
    id: str
    name: str
    description: Optional[str] = None
    is_allowed: bool = False
    parent_id: Optional[str] = None
    level: int = 0
    
    def __post_init__(self):
        # Clean up strings
        self.id = str(self.id).strip()
        self.name = self.name.strip()
        
        if self.description:
            self.description = self.description.strip()
        
        # Validate required fields
        if not self.id:
            raise ValueError("Location ID cannot be empty")
        
        if not self.name:
            raise ValueError("Location name cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_allowed': self.is_allowed,
            'parent_id': self.parent_id,
            'level': self.level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            is_allowed=data.get('is_allowed', False),
            parent_id=data.get('parent_id'),
            level=data.get('level', 0)
        )
    
    def matches_filter(self, filter_mode: str, marker: str) -> bool:
        """Check if location matches the filter criteria"""
        if filter_mode == 'none':
            return False
        elif filter_mode == 'all':
            return True
        elif filter_mode == 'marker':
            return marker in (self.description or '')
        else:
            return False
    
    def get_display_name(self) -> str:
        """Get display name with description if available"""
        if self.description:
            return f"{self.name}: {self.description}"
        return self.name


class LocationManager:
    """Manager for location operations"""
    
    def __init__(self, locations: List[Location]):
        self.locations = locations
        self._by_id = {loc.id: loc for loc in locations}
        self._by_name = {loc.name: loc for loc in locations}
    
    def get_by_id(self, location_id: str) -> Optional[Location]:
        """Get location by ID"""
        return self._by_id.get(location_id)
    
    def get_by_name(self, name: str) -> Optional[Location]:
        """Get location by name"""
        return self._by_name.get(name)
    
    def get_allowed_locations(self, filter_mode: str, marker: str) -> List[Location]:
        """Get all allowed locations based on filter"""
        return [loc for loc in self.locations if loc.matches_filter(filter_mode, marker)]
    
    def get_location_names(self, include_descriptions: bool = True) -> List[str]:
        """Get list of location names for AI prompts"""
        if include_descriptions:
            return [loc.get_display_name() for loc in self.locations]
        return [loc.name for loc in self.locations]
    
    def find_best_match(self, suggested_name: str) -> Optional[Location]:
        """Find best matching location for suggested name"""
        # Exact match first
        if suggested_name in self._by_name:
            return self._by_name[suggested_name]
        
        # Partial match
        for loc in self.locations:
            if suggested_name.lower() in loc.name.lower():
                return loc
        
        # Return first location as fallback
        return self.locations[0] if self.locations else None
