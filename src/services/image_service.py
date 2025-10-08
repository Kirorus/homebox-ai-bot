"""
Image processing and validation service
"""

import os
import logging
from typing import Tuple, Optional
from PIL import Image
from pathlib import Path

from utils.validators import ImageValidator
from utils.file_utils import FileManager

logger = logging.getLogger(__name__)


class ImageService:
    """Service for image processing and validation"""
    
    def __init__(self, max_size_mb: int = 20, max_dimensions: int = 4096):
        self.max_size_mb = max_size_mb
        self.max_dimensions = max_dimensions
        self.validator = ImageValidator(max_size_mb, max_dimensions)
        self.file_manager = FileManager()
    
    def validate_image(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate image file
        
        Returns:
            (is_valid, error_message)
        """
        return self.validator.validate(file_path)
    
    def resize_image_if_needed(self, image_path: str, max_size: int = 2048) -> str:
        """
        Resize image if it's too large
        
        Returns:
            Path to resized image (original if no resize needed)
        """
        try:
            with Image.open(image_path) as img:
                # Check if resize is needed
                if img.width <= max_size and img.height <= max_size:
                    return image_path
                
                # Calculate new dimensions maintaining aspect ratio
                if img.width > img.height:
                    new_width = max_size
                    new_height = int((img.height * max_size) / img.width)
                else:
                    new_height = max_size
                    new_width = int((img.width * max_size) / img.height)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                resized_path = self.file_manager.get_temp_file_path('resized', '.jpg')
                resized_img.save(resized_path, 'JPEG', quality=85)
                
                logger.info(f"Image resized from {img.width}x{img.height} to {new_width}x{new_height}")
                return resized_path
                
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return image_path
    
    def optimize_image(self, image_path: str) -> str:
        """
        Optimize image for AI processing
        
        Returns:
            Path to optimized image
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                optimized_path = self.resize_image_if_needed(image_path)
                
                # If no resize was needed, create optimized copy
                if optimized_path == image_path:
                    optimized_path = self.file_manager.get_temp_file_path('optimized', '.jpg')
                    img.save(optimized_path, 'JPEG', quality=90, optimize=True)
                
                logger.info(f"Image optimized: {optimized_path}")
                return optimized_path
                
        except Exception as e:
            logger.error(f"Failed to optimize image: {e}")
            return image_path
    
    def get_image_info(self, image_path: str) -> dict:
        """Get image information"""
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size_bytes': os.path.getsize(image_path)
                }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return {}
    
    def cleanup_temp_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup file {file_path}: {e}")
