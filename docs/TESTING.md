# 🧪 Тестирование HomeBox AI Bot

Этот документ описывает стратегию тестирования и инструкции по запуску тестов для HomeBox AI Bot.

## 📋 Содержание

- [Структура тестов](#структура-тестов)
- [Типы тестов](#типы-тестов)
- [Запуск тестов](#запуск-тестов)
- [Покрытие кода](#покрытие-кода)
- [Написание тестов](#написание-тестов)
- [Лучшие практики](#лучшие-практики)

## 📁 Структура тестов

```
tests/
├── conftest.py              # Общие фикстуры и настройки pytest
├── unit/                    # Unit тесты
│   ├── test_ai_service.py
│   ├── test_database_service.py
│   └── test_homebox_service.py
├── handlers/                # Тесты обработчиков
│   └── test_photo_handler.py
├── integration/             # Интеграционные тесты
│   └── test_full_workflow.py
├── examples/                # Примеры тестов
│   └── test_example.py
└── fixtures/                # Дополнительные фикстуры
```

## 🎯 Типы тестов

### Unit тесты
- **Назначение**: Тестирование отдельных компонентов в изоляции
- **Покрытие**: Сервисы (AI, Database, HomeBox, Image)
- **Моки**: Все внешние зависимости замокированы
- **Маркер**: `@pytest.mark.unit`

### Интеграционные тесты
- **Назначение**: Тестирование взаимодействия между компонентами
- **Покрытие**: Полные рабочие процессы
- **Моки**: Минимальные, только внешние API
- **Маркер**: `@pytest.mark.integration`

### Тесты обработчиков
- **Назначение**: Тестирование логики обработки команд Telegram
- **Покрытие**: Handlers, состояния, клавиатуры
- **Моки**: Telegram Bot API, внешние сервисы
- **Маркер**: `@pytest.mark.handlers`

## 🚀 Запуск тестов

### Установка зависимостей

```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Установить зависимости для тестирования
pip install -r requirements.txt
```

### Основные команды

```bash
# Запустить все тесты
./run_tests.sh

# Запустить только unit тесты
./run_tests.sh unit
pytest tests/unit/ -v

# Запустить только интеграционные тесты
./run_tests.sh integration
pytest tests/integration/ -v

# Запустить только тесты обработчиков
./run_tests.sh handlers
pytest tests/handlers/ -v

# Запустить быстрые тесты (исключить медленные)
./run_tests.sh fast
pytest tests/ -v -m "not slow"

# Запустить тесты с подробным покрытием
./run_tests.sh coverage
pytest tests/ --cov=src --cov-report=html
```

### Прямые команды pytest

```bash
# Все тесты с покрытием
pytest tests/ -v --cov=src --cov-report=term-missing

# Конкретный файл тестов
pytest tests/unit/test_ai_service.py -v

# Конкретный тест
pytest tests/unit/test_ai_service.py::TestAIService::test_encode_image -v

# Тесты с определенным маркером
pytest tests/ -v -m unit
pytest tests/ -v -m integration
pytest tests/ -v -m "not slow"

# Тесты с отладкой
pytest tests/ -v -s --pdb

# Параллельный запуск (требует pytest-xdist)
pytest tests/ -n auto
```

## 📊 Покрытие кода

### Текущее покрытие
Цель: **80%+ покрытие кода**

### Генерация отчетов

```bash
# HTML отчет (открыть htmlcov/index.html)
pytest tests/ --cov=src --cov-report=html

# XML отчет для CI/CD
pytest tests/ --cov=src --cov-report=xml

# Терминальный отчет
pytest tests/ --cov=src --cov-report=term-missing
```

### Исключения из покрытия
- Файлы конфигурации
- Точки входа (main.py)
- Миграции
- Тестовые файлы

## ✍️ Написание тестов

### Структура теста

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestComponentName:
    """Test cases for ComponentName"""
    
    @pytest.fixture
    def component(self, dependencies):
        """Create component for testing"""
        return ComponentName(dependencies)
    
    @pytest.mark.asyncio
    async def test_method_name(self, component):
        """Test specific method functionality"""
        # Arrange
        input_data = "test"
        expected_result = "expected"
        
        # Act
        result = await component.method(input_data)
        
        # Assert
        assert result == expected_result
```

### Фикстуры

```python
# В conftest.py
@pytest.fixture
async def database_service(temp_db):
    """Create database service for testing"""
    service = DatabaseService(temp_db)
    await service.init_database()
    yield service
    await service.close()

# Использование в тестах
def test_something(database_service):
    # database_service автоматически создается и очищается
    pass
```

### Моки

```python
# Мок внешнего API
with patch.object(ai_service, 'analyze_image', return_value=mock_analysis):
    result = await ai_service.analyze_image(image_path, locations, "en")
    assert result == mock_analysis

# Мок асинхронной функции
with patch.object(service, 'async_method', new_callable=AsyncMock) as mock_method:
    mock_method.return_value = "expected_result"
    result = await service.async_method()
    assert result == "expected_result"
```

### Параметризованные тесты

```python
@pytest.mark.parametrize("input_value,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_scenarios(input_value, expected):
    result = process_input(input_value)
    assert result == expected
```

## 🎯 Лучшие практики

### 1. Именование тестов
```python
def test_should_return_error_when_invalid_input_provided():
    """Тест должен возвращать ошибку при неверном входе"""
    pass

def test_should_create_user_when_valid_data_provided():
    """Тест должен создавать пользователя при валидных данных"""
    pass
```

### 2. Структура AAA
```python
def test_example():
    # Arrange - подготовка данных
    input_data = {"name": "test"}
    expected_result = "processed_test"
    
    # Act - выполнение действия
    result = process_data(input_data)
    
    # Assert - проверка результата
    assert result == expected_result
```

### 3. Изоляция тестов
```python
# Каждый тест должен быть независимым
def test_1():
    # Не зависит от test_2
    pass

def test_2():
    # Не зависит от test_1
    pass
```

### 4. Моки и стабы
```python
# Мокайте внешние зависимости
with patch('external_api.call'):
    result = internal_function()
    assert result is not None

# Используйте фикстуры для сложных объектов
def test_with_fixture(database_service):
    # database_service уже настроен
    pass
```

### 5. Асинхронные тесты
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 6. Обработка исключений
```python
def test_exception_handling():
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises_exception("invalid")
```

### 7. Тестовые данные
```python
# Используйте фикстуры для тестовых данных
@pytest.fixture
def sample_user_data():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "age": 25
    }

def test_user_creation(sample_user_data):
    user = create_user(sample_user_data)
    assert user.name == "Test User"
```

## 🔧 Настройка CI/CD

### GitHub Actions пример

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
      with:
        file: ./coverage.xml
```

## 📈 Метрики качества

### Цели покрытия
- **Общее покрытие**: 80%+
- **Критический код**: 95%+
- **Сервисы**: 90%+
- **Обработчики**: 85%+

### Качество тестов
- Все публичные методы покрыты тестами
- Граничные случаи протестированы
- Ошибки обрабатываются корректно
- Тесты выполняются быстро (< 1 сек на тест)

## 🐛 Отладка тестов

### Полезные флаги pytest

```bash
# Остановить на первой ошибке
pytest tests/ -x

# Запустить только неудачные тесты
pytest tests/ --lf

# Показать локальные переменные при ошибке
pytest tests/ -l

# Запустить отладчик при ошибке
pytest tests/ --pdb

# Очень подробный вывод
pytest tests/ -vvv
```

### Логирование в тестах

```python
import logging

def test_with_logging(caplog):
    with caplog.at_level(logging.INFO):
        function_that_logs()
    
    assert "Expected log message" in caplog.text
```

## 📚 Дополнительные ресурсы

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Примечание**: Этот документ обновляется по мере развития системы тестирования. Всегда проверяйте актуальную версию перед написанием новых тестов.
