"""
File management utilities
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """File management utilities"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'temp')
        self._ensure_temp_dir()
    
    def _ensure_temp_dir(self):
        """Ensure temp directory exists"""
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_temp_file_path(self, prefix: str = 'temp', suffix: str = '.tmp') -> str:
        """Get a unique temporary file path"""
        filename = f"{prefix}_{uuid.uuid4().hex}{suffix}"
        return os.path.join(self.temp_dir, filename)
    
    def create_temp_file(self, content: bytes = b'', prefix: str = 'temp', suffix: str = '.tmp') -> str:
        """Create a temporary file with content"""
        file_path = self.get_temp_file_path(prefix, suffix)
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path
    
    def cleanup_temp_files(self, pattern: str = 'temp_*') -> int:
        """Clean up temporary files matching pattern"""
        cleaned_count = 0
        try:
            for file_path in Path(self.temp_dir).glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    cleaned_count += 1
                    logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
        
        return cleaned_count
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Clean up files older than specified hours"""
        import time
        cleaned_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for file_path in Path(self.temp_dir).glob('temp_*'):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
        
        return cleaned_count
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def ensure_directory(self, directory: str):
        """Ensure directory exists"""
        os.makedirs(directory, exist_ok=True)
    
    def is_safe_path(self, path: str) -> bool:
        """Check if path is safe (no directory traversal)"""
        try:
            # Resolve the path and check if it's within allowed directory
            resolved_path = os.path.realpath(path)
            return resolved_path.startswith(os.path.realpath(self.temp_dir))
        except (OSError, ValueError):
            return False
