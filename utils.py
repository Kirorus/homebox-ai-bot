"""
Utility functions for the HomeBox AI Bot
"""
import asyncio
import logging
from typing import Callable, Any, Optional
import functools

logger = logging.getLogger(__name__)

def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Декоратор для повторных попыток выполнения асинхронных функций
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками в секундах
        backoff_factor: Коэффициент увеличения задержки
        exceptions: Кортеж исключений, при которых нужно повторять попытки
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise e
                    
                    logger.warning(f"Function {func.__name__} failed on attempt {attempt + 1}: {e}. Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
                    
            raise last_exception
            
        return wrapper
    return decorator

def format_file_size(size_bytes: int) -> str:
    """Форматирует размер файла в читаемый вид"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов"""
    import re
    # Удаляем недопустимые символы для файловых систем
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Ограничиваем длину
    if len(sanitized) > 100:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:95] + ('.' + ext if ext else '')
    
    return sanitized or 'unnamed'

class RateLimiter:
    """Простой ограничитель частоты запросов"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Ждет, если необходимо, чтобы не превысить лимит"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # Удаляем старые запросы
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.time_window]
            
            # Если достигли лимита, ждем
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    # Обновляем список после ожидания
                    now = asyncio.get_event_loop().time()
                    self.requests = [req_time for req_time in self.requests 
                                   if now - req_time < self.time_window]
            
            # Добавляем текущий запрос
            self.requests.append(now)

def validate_image_file(file_path: str) -> tuple[bool, str]:
    """
    Проверяет, является ли файл валидным изображением
    
    Returns:
        (is_valid, error_message)
    """
    import os
    from PIL import Image
    
    # Проверяем существование файла
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    # Проверяем размер файла (максимум 20MB)
    file_size = os.path.getsize(file_path)
    if file_size > 20 * 1024 * 1024:
        return False, f"File too large: {format_file_size(file_size)}"
    
    try:
        # Пытаемся открыть как изображение
        with Image.open(file_path) as img:
            # Проверяем формат
            if img.format not in ['JPEG', 'PNG', 'WEBP']:
                return False, f"Unsupported image format: {img.format}"
            
            # Проверяем размеры
            if img.width > 4096 or img.height > 4096:
                return False, f"Image too large: {img.width}x{img.height}"
            
            # Проверяем, что изображение можно прочитать
            img.verify()
            
        return True, ""
        
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"
