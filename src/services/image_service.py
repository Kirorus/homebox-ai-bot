"""
Image processing and validation service
"""

import os
import logging
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
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

    def add_diagonal_watermark(self, image_path: str, text: str = "УДАЛЕНО", max_dim: int = 1280) -> Optional[str]:
        """
        Add a semi-transparent diagonal watermark across the image.
        Returns path to the new watermarked image, or None on failure.
        """
        try:
            with Image.open(image_path).convert("RGBA") as base:
                # Downscale large images to speed up Telegram upload
                width, height = base.size
                if max(width, height) > max_dim:
                    if width >= height:
                        new_w = max_dim
                        new_h = int(height * (max_dim / width))
                    else:
                        new_h = max_dim
                        new_w = int(width * (max_dim / height))
                    base = base.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    width, height = base.size
                overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
                draw = ImageDraw.Draw(overlay)

                # Choose a scalable font and size so text spans the diagonal
                # Prefer widely available Unicode fonts with Cyrillic support
                env_font = os.getenv("WATERMARK_FONT")
                # Prefer project-bundled NotoSans first
                project_dir = Path(__file__).resolve().parents[2]
                bundled_bold = project_dir / 'assets' / 'fonts' / 'NotoSans-Bold.ttf'
                bundled_regular = project_dir / 'assets' / 'fonts' / 'NotoSans-Regular.ttf'
                fonts_to_try = [
                    str(bundled_bold) if bundled_bold.exists() else None,
                    str(bundled_regular) if bundled_regular.exists() else None,
                    env_font if env_font else None,
                    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
                    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
                    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                    "/usr/share/fonts/truetype/roboto/hinted/Roboto-Bold.ttf",
                    "/usr/share/fonts/truetype/roboto/hinted/Roboto-Regular.ttf",
                    "/usr/share/fonts/truetype/pt/PTS75F.ttf",  # PT Sans Bold
                    "/usr/share/fonts/truetype/pt/PTS55F.ttf",  # PT Sans
                    "NotoSans-Bold.ttf",
                    "LiberationSans-Bold.ttf",
                    "FreeSansBold.ttf",
                    "Ubuntu-B.ttf",
                    "Roboto-Bold.ttf",
                    "PTSans-Bold.ttf",
                ]
                def load_font(size: int) -> Optional[ImageFont.FreeTypeFont]:
                    for fp in fonts_to_try:
                        if not fp:
                            continue
                        try:
                            return ImageFont.truetype(fp, size)
                        except Exception:
                            continue
                    return None

                # Target width is larger than diagonal to ensure edge-to-edge after rotation
                import math
                target_width = math.hypot(width, height) * 2.4
                font_size = max(24, int(min(width, height) * 0.22))
                font = load_font(font_size)
                # If no TTF font available, fallback once and continue (cannot scale default)
                scalable = font is not None
                if not scalable:
                    font = ImageFont.load_default()

                # Increase font size until it spans the diagonal or until a safety cap
                # Scale font size multiplicatively using width measurements
                attempts = 0
                while scalable and attempts < 10:
                    stroke_w = max(4, int(font_size * 0.12))
                    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
                    text_w = max(1, bbox[2] - bbox[0])
                    if text_w >= target_width:
                        break
                    factor = min(3.0, (target_width / text_w) * 1.05)
                    new_size = min(10000, max(font_size + 1, int(font_size * factor)))
                    new_font = load_font(new_size)
                    if new_font is None:
                        break
                    font_size = new_size
                    font = new_font
                    attempts += 1

                # Final stroke width after size selection
                stroke_w = max(3, int(font_size * 0.12))

                # Draw the text centered before rotation; nudge slightly so corners reach edges
                bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x = (width - text_w) // 2
                y = (height - text_h) // 2
                x -= int(width * 0.02)
                y -= int(height * 0.02)

                # Semi-transparent red text with white stroke (bold)
                draw.text(
                    (x, y),
                    text,
                    font=font,
                    fill=(255, 0, 0, 170),
                    stroke_width=stroke_w,
                    stroke_fill=(255, 255, 255, 240),
                )

                # Rotate overlay to align with the actual image diagonal
                angle_deg = math.degrees(math.atan2(height, width))
                rotated = overlay.rotate(angle_deg, expand=True)

                # Center-crop back to the original image size
                rw, rh = rotated.size
                left = (rw - width) // 2
                top = (rh - height) // 2
                rotated_cropped = rotated.crop((left, top, left + width, top + height))

                # Composite the watermark onto the original image
                watermarked = Image.alpha_composite(base, rotated_cropped)

                # Save to temp file
                output_path = self.file_manager.get_temp_file_path('deleted', '.jpg')
                watermarked.convert("RGB").save(output_path, "JPEG", quality=78, optimize=True)
                return output_path
        except Exception as e:
            logger.error(f"Failed to add diagonal watermark: {e}")
            return None
    
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
