#!/usr/bin/env python3
"""
Простой тест загрузки фотографий с фиксированным ID предмета
"""
import asyncio
import sys
import os
from PIL import Image
import tempfile

# Добавляем текущую директорию в путь
sys.path.append('.')

from homebox_api import HomeboxAPI
import config

async def simple_test():
    print("🚀 Простой тест загрузки фотографий...")
    
    # Создаем тестовое изображение
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        img = Image.new('RGB', (50, 50), color='blue')
        img.save(temp_file.name, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Инициализируем API
        print("📡 Подключение к API...")
        api = HomeboxAPI()
        
        # Используем фиксированный ID предмета (из логов)
        item_id = "b411f2df-916c-4a49-8e8f-fa1b7a518865"  # Из предыдущих логов
        
        print(f"🧪 Тестируем загрузку для предмета: {item_id}")
        
        # Тестируем загрузку
        success = await api.upload_photo(item_id, temp_path)
        
        if success:
            print('✅ Загрузка прошла успешно!')
            return True
        else:
            print(f'❌ Загрузка не удалась: {api.last_error}')
            return False
    
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        return False
    
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    result = asyncio.run(simple_test())
    if result:
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n💥 Тест не прошел")
