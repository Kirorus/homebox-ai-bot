#!/usr/bin/env python3
"""
Тестирование создания предметов в HomeBox API
"""
import asyncio
import sys
import json

# Добавляем текущую директорию в путь
sys.path.append('.')

from homebox_api import HomeboxAPI
import config

async def test_create_item():
    print("🧪 Тестирование создания предметов в HomeBox...")
    
    try:
        # Инициализируем API
        print("📡 Подключение к API...")
        api = HomeboxAPI()
        
        # Получаем локации
        print("📍 Получение локаций...")
        locations = await api.get_locations()
        if not locations:
            print('❌ Не удалось получить локации')
            return False
        
        print(f"✅ Найдено локаций: {len(locations)}")
        
        # Показываем первые несколько локаций
        print("\n📋 Доступные локации:")
        for i, location in enumerate(locations[:5]):
            print(f"  {i+1}. {location.get('name', 'Без имени')} (ID: {location.get('id', 'N/A')})")
        
        # Используем первую локацию для тестирования
        test_location = locations[0]
        location_id = test_location['id']
        location_name = test_location.get('name', 'Без имени')
        
        print(f"\n🧪 Тестируем создание предмета в локации: {location_name}")
        
        # Тестируем создание предмета
        item_result = await api.create_item(
            name="Test Item API",
            description="Тестовый предмет для проверки API",
            location_id=str(location_id)
        )
        
        if 'error' in item_result:
            print(f"❌ Ошибка создания предмета: {item_result['error']}")
            print(f"🔍 Детали ошибки: {api.last_error}")
            return False
        else:
            item_id = item_result.get('id')
            item_name = item_result.get('name', 'N/A')
            print(f"✅ Предмет успешно создан!")
            print(f"   ID: {item_id}")
            print(f"   Название: {item_name}")
            return True
    
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_create_item())
    if result:
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n💥 Тест не прошел")
