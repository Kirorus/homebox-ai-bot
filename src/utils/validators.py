"""
Input validation utilities
"""

import os
import re
from typing import Tuple, Optional
from PIL import Image


class ImageValidator:
    """Image file validation"""
    
    def __init__(self, max_size_mb: int = 20, max_dimensions: int = 4096):
        self.max_size_mb = max_size_mb
        self.max_dimensions = max_dimensions
        self.allowed_formats = ['JPEG', 'PNG', 'WEBP']
    
    def validate(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate image file
        
        Returns:
            (is_valid, error_message)
        """
        # Check file existence
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size_bytes = self.max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File too large: {self._format_size(file_size)} (max {self.max_size_mb}MB)"
        
        try:
            # Try to open as image
            with Image.open(file_path) as img:
                # Check format
                if img.format not in self.allowed_formats:
                    return False, f"Unsupported image format: {img.format}. Allowed: {', '.join(self.allowed_formats)}"
                
                # Check dimensions
                if img.width > self.max_dimensions or img.height > self.max_dimensions:
                    return False, f"Image too large: {img.width}x{img.height} (max {self.max_dimensions}x{self.max_dimensions})"
                
                # Check that image can be read
                img.verify()
                
            return True, ""
            
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"


class InputValidator:
    """Input data validation"""
    
    @staticmethod
    def validate_item_name(name: str) -> Tuple[bool, str]:
        """Validate item name"""
        if not name or not name.strip():
            return False, "Item name cannot be empty"
        
        name = name.strip()
        if len(name) > 50:
            return False, "Item name too long (max 50 characters)"
        
        # Check for dangerous characters
        if re.search(r'[<>:"/\\|?*]', name):
            return False, "Item name contains invalid characters"
        
        return True, ""
    
    @staticmethod
    def validate_item_description(description: str) -> Tuple[bool, str]:
        """Validate item description"""
        if not description or not description.strip():
            return False, "Item description cannot be empty"
        
        description = description.strip()
        if len(description) > 200:
            return False, "Item description too long (max 200 characters)"
        
        return True, ""
    
    @staticmethod
    def validate_location_id(location_id: str) -> Tuple[bool, str]:
        """Validate location ID"""
        if not location_id or not str(location_id).strip():
            return False, "Location ID cannot be empty"
        
        # Check if it's a valid ID (numeric or alphanumeric)
        if not re.match(r'^[a-zA-Z0-9_-]+$', str(location_id).strip()):
            return False, "Invalid location ID format"
        
        return True, ""
    
    @staticmethod
    def validate_user_id(user_id: int) -> Tuple[bool, str]:
        """Validate user ID"""
        if not isinstance(user_id, int) or user_id <= 0:
            return False, "Invalid user ID"
        
        return True, ""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove invalid characters for file systems
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        if len(sanitized) > 100:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            sanitized = name[:95] + ('.' + ext if ext else '')
        
        return sanitized or 'unnamed'
    
    @staticmethod
    def validate_language_code(lang: str) -> Tuple[bool, str]:
        """Validate language code"""
        if lang not in ['ru', 'en']:
            return False, "Invalid language code. Must be 'ru' or 'en'"
        
        return True, ""
    
    @staticmethod
    def validate_model_name(model: str, available_models: list) -> Tuple[bool, str]:
        """Validate model name"""
        if model not in available_models:
            return False, f"Invalid model. Available: {', '.join(available_models)}"
        
        return True, ""
