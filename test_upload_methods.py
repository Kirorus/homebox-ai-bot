#!/usr/bin/env python3
"""
Тестирование всех методов загрузки фотографий
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

async def test_all_methods():
    print("🚀 Тестирование методов загрузки фотографий...")
    
    # Создаем тестовое изображение
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        img = Image.new('RGB', (50, 50), color='red')
        img.save(temp_file.name, 'JPEG')
        temp_path = temp_file.name
    
    try:
        # Инициализируем API
        print("📡 Подключение к API...")
        api = HomeboxAPI()
        
        # Получаем локации
        print("📍 Получение локаций...")
        locations = await api.get_locations()
        if not locations:
            print('❌ Не удалось получить локации')
            return
        
        print(f"✅ Найдено локаций: {len(locations)}")
        
        # Используем существующий предмет для тестирования
        print("📦 Поиск существующего предмета для тестирования...")
        
        # Попробуем создать предмет, если не получается - используем любой существующий
        item_result = await api.create_item(
            name='Upload Test Item',
            description='Testing upload methods',
            location_id=str(locations[0]['id'])
        )
        
        if 'error' in item_result:
            print(f'⚠️ Не удалось создать предмет: {item_result["error"]}')
            print("🔍 Попробуем использовать существующий предмет...")
            
            # Получаем список предметов
            try:
                session = await api._get_session()
                async with session.get(
                    f'{api.base_url}/api/v1/items',
                    headers=api.headers
                ) as response:
                    if response.status == 200:
                        items = await response.json()
                        print(f'🔍 Получено предметов: {len(items) if items else 0}')
                        print(f'🔍 Первый предмет: {items[0] if items else "None"}')
                        if items and len(items) > 0:
                            # Ищем предмет с валидным ID
                            valid_item = None
                            for item in items:
                                if isinstance(item, dict) and item.get('id') and str(item['id']) != '0':
                                    valid_item = item
                                    break
                                elif isinstance(item, str) and item and item != '0':
                                    valid_item = {'id': item}
                                    break
                            
                            if valid_item:
                                item_id = str(valid_item['id'])
                                print(f'✅ Используем существующий предмет: {item_id}')
                            else:
                                print('❌ Нет предметов с валидными ID для тестирования')
                                return
                        else:
                            print('❌ Нет доступных предметов для тестирования')
                            return
                    else:
                        print(f'❌ Не удалось получить список предметов: HTTP {response.status}')
                        return
            except Exception as e:
                print(f'❌ Ошибка при получении предметов: {e}')
                return
        else:
            item_id = item_result.get('id')
            print(f'✅ Создан тестовый предмет: {item_id}')
        
        # Тестируем единственный метод
        methods = [
            ('Raw HTTP Upload', api.upload_photo)
        ]
        
        working_methods = []
        
        for name, method in methods:
            print(f'\n🧪 Тестируем: {name}')
            try:
                success = await method(item_id, temp_path)
                if success:
                    print(f'✅ {name}: РАБОТАЕТ!')
                    working_methods.append((name, method))
                else:
                    print(f'❌ {name}: Не работает - {api.last_error}')
            except Exception as e:
                print(f'❌ {name}: Ошибка - {e}')
        
        print(f'\n📊 Результаты:')
        print(f'Рабочих методов: {len(working_methods)}')
        for name, _ in working_methods:
            print(f'  ✅ {name}')
        
        if working_methods:
            best_method = working_methods[0]
            print(f'\n🏆 Лучший метод: {best_method[0]}')
            return best_method[0]
        else:
            print('\n❌ Ни один метод не работает')
            return None
    
    except Exception as e:
        print(f'❌ Общая ошибка: {e}')
        return None
    
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    result = asyncio.run(test_all_methods())
    if result:
        print(f"\n🎯 Рекомендуется использовать: {result}")
    else:
        print("\n⚠️ Требуется дополнительная диагностика")
