import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import AsyncOpenAI
import base64
import os
import json

import config
from homebox_api import HomeboxAPI
from i18n import t
from utils import validate_image_file, format_file_size
from database import db

# Enhanced logging setup
logging.basicConfig(
    level=logging.DEBUG,  # Изменено на DEBUG для более детального логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialization
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()
openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
homebox_api = HomeboxAPI()

# FSM states
class ItemStates(StatesGroup):
    waiting_for_photo = State()
    confirming_data = State()
    editing_name = State()
    editing_description = State()
    selecting_location = State()

# In-memory items storage (temporary data during processing)
items_data = {}

def log_error(error: Exception, context: str = "", user_id: int = None):
    """Enhanced error logging with context and user information"""
    error_info = {
        'timestamp': datetime.now().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'user_id': user_id,
        'traceback': traceback.format_exc()
    }
    logger.error(f"Error in {context}: {error}", extra=error_info)
    
    # Also log to file in JSON format for better parsing
    with open('errors.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps(error_info, ensure_ascii=False) + '\n')

def log_user_action(action: str, user_id: int, details: dict = None):
    """Log user actions for analytics and debugging"""
    action_info = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'user_id': user_id,
        'details': details or {}
    }
    logger.info(f"User action: {action} by user {user_id}", extra=action_info)

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in config.ALLOWED_USER_IDS

async def get_uptime() -> str:
    """Возвращает время работы бота в читаемом формате"""
    stats = await db.get_bot_stats()
    start_time_str = stats.get('start_time', datetime.now().isoformat())
    start_time = datetime.fromisoformat(start_time_str)
    uptime = datetime.now() - start_time
    
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м"
    else:
        return f"{minutes}м {seconds}с"

async def cleanup_temp_files():
    """Очищает временные файлы"""
    temp_files = [f for f in os.listdir('.') if f.startswith('temp_')]
    removed_count = 0
    
    for temp_file in temp_files:
        try:
            # Проверяем возраст файла (старше 1 часа)
            file_time = datetime.fromtimestamp(os.path.getmtime(temp_file))
            if datetime.now() - file_time > timedelta(hours=1):
                os.remove(temp_file)
                removed_count += 1
        except Exception as e:
            logger.error(f"Error removing temp file {temp_file}: {e}")
    
    return removed_count

async def update_progress_message(message: Message, progress_msg: Message, step: str, lang: str):
    """Обновляет сообщение о прогрессе"""
    try:
        await progress_msg.edit_text(t(lang, f'progress.{step}'))
    except Exception as e:
        logger.warning(f"Failed to update progress message: {e}")
        # Если не удалось обновить, отправляем новое сообщение
        try:
            await progress_msg.delete()
        except:
            pass
        return await message.answer(t(lang, f'progress.{step}'))
    return progress_msg

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def analyze_image(image_path: str, locations: list, lang: str = 'ru', model: str | None = None, caption: str | None = None) -> dict:
    """Analyze image via OpenAI Vision to extract item metadata."""
    base64_image = encode_image(image_path)
    
    locations_text = "\n".join([f"- {loc['name']}" for loc in locations])
    
    # Добавляем информацию о caption в промпт, если она есть
    caption_info = ""
    if caption and caption.strip():
        if lang == 'en':
            caption_info = f"\n\nAdditional information from the photo description: \"{caption}\"\nUse this information to help identify the item more accurately."
        else:
            caption_info = f"\n\nДополнительная информация из описания фото: \"{caption}\"\nИспользуй эту информацию для более точного определения предмета."

    if lang == 'en':
        prompt = f"""You are an expert at identifying household items and organizing them. Analyze this image carefully and provide:

1. **Item Name**: A concise, descriptive name (max 50 chars). Be specific about brand, model, or type when visible.
2. **Description**: A detailed description (max 200 chars) including material, color, condition, and any distinguishing features.
3. **Storage Location**: Choose the most appropriate location from the available options based on the item's typical use and storage requirements.

**Analysis Guidelines:**
- Look for brand names, model numbers, or text on the item
- Consider the item's size, material, and typical usage
- Think about where this item would logically be stored in a home
- If it's a tool, consider the workspace; if it's clothing, consider the wardrobe area
- For electronics, consider tech storage areas

**Available Locations:**
{locations_text}{caption_info}

**Important:** Respond ONLY with valid JSON in this exact format:
{{
    "name": "specific item name",
    "description": "detailed description with material, color, condition",
    "suggested_location": "exact location name from the list above"
}}"""
    else:
        prompt = f"""Ты эксперт по определению предметов домашнего обихода и их организации. Внимательно проанализируй это изображение и предоставь:

1. **Название предмета**: Краткое, описательное название (до 50 символов). Будь конкретным в отношении бренда, модели или типа, когда это видно.
2. **Описание**: Подробное описание (до 200 символов), включающее материал, цвет, состояние и отличительные особенности.
3. **Место хранения**: Выбери наиболее подходящее место из доступных вариантов, основываясь на типичном использовании предмета и требованиях к хранению.

**Рекомендации по анализу:**
- Ищи названия брендов, модели или текст на предмете
- Учитывай размер, материал и типичное использование предмета
- Думай о том, где логично хранить этот предмет в доме
- Если это инструмент, подумай о рабочем пространстве; если одежда - о гардеробе
- Для электроники рассмотри области хранения техники

**Доступные локации:**
{locations_text}{caption_info}

**Важно:** Отвечай ТОЛЬКО валидным JSON в точном формате:
{{
    "name": "конкретное название предмета",
    "description": "подробное описание с материалом, цветом, состоянием",
    "suggested_location": "точное название локации из списка выше"
}}"""

    try:
        # Используем выбранную модель или дефолтную
        selected_model = model or config.DEFAULT_MODEL
        logger.info(f"Analyzing image with model: {selected_model}")
        
        response = await openai_client.chat.completions.create(
            model=selected_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info(f"Image analysis successful: {result}")
        return result
        
    except json.JSONDecodeError as e:
        log_error(e, "JSON parsing error in image analysis")
        return {
            "name": "Unknown item" if lang == 'en' else "Неизвестный предмет",
            "description": "Failed to parse response" if lang == 'en' else "Ошибка обработки ответа",
            "suggested_location": locations[0]['name'] if locations else ("Unknown" if lang == 'en' else "Unknown")
        }
    except Exception as e:
        log_error(e, "Image analysis failed")
        return {
            "name": "Unknown item" if lang == 'en' else "Неизвестный предмет",
            "description": "Failed to recognize" if lang == 'en' else "Не удалось распознать",
            "suggested_location": locations[0]['name'] if locations else ("Unknown" if lang == 'en' else "Unknown")
        }

def settings_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ru_label = "🇷🇺 Русский" + (" ✓" if current_lang == 'ru' else "")
    en_label = "🇬🇧 English" + (" ✓" if current_lang == 'en' else "")
    builder.row(InlineKeyboardButton(text=ru_label, callback_data="lang_ru"))
    builder.row(InlineKeyboardButton(text=en_label, callback_data="lang_en"))
    return builder.as_markup()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'access.denied'))
        return
    
    settings = await db.get_user_settings(message.from_user.id)
    await message.answer(
        t(settings.get('lang', 'ru'), 'settings.title'),
        reply_markup=settings_keyboard(settings.get('lang', 'ru'))
    )
    await message.answer(
        t(settings.get('lang', 'ru'), 'settings.choose_model'),
        reply_markup=models_keyboard(settings.get('model', config.DEFAULT_MODEL), 0)
    )

@router.message(Command(commands=["myid", "id"]))
async def cmd_myid(message: Message):
    """Отправить пользователю его Telegram ID (доступно всем)."""
    user_settings = await db.get_user_settings(message.from_user.id)
    lang = user_settings.get('lang', 'ru')
    await message.answer(t(lang, 'cmd.myid', user_id=message.from_user.id))

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать статистику бота (только для администраторов)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    lang = user_settings.get('lang', 'ru')
    stats = await db.get_bot_stats()
    
    stats_text = (
        f"{t(lang, 'admin.stats.title')}\n\n"
        f"{t(lang, 'admin.stats.users', count=len(stats.get('users_registered', [])))}\n"
        f"{t(lang, 'admin.stats.items', count=stats.get('items_processed', 0))}\n"
        f"{t(lang, 'admin.stats.sessions', count=len(items_data))}\n"
        f"{t(lang, 'admin.stats.uptime', uptime=await get_uptime())}\n\n"
        f"📈 Всего запросов: {stats.get('total_requests', 0)}"
    )
    
    await message.answer(stats_text, parse_mode="Markdown")

@router.message(Command("cleanup"))
async def cmd_cleanup(message: Message):
    """Очистить временные файлы (только для администраторов)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    lang = user_settings.get('lang', 'ru')
    
    try:
        removed_count = await cleanup_temp_files()
        await message.answer(t(lang, 'admin.cleanup.done', files=removed_count))
        log_user_action("admin_cleanup", message.from_user.id, {"files_removed": removed_count})
    except Exception as e:
        await message.answer(t(lang, 'admin.cleanup.error', error=str(e)))
        log_error(e, "admin cleanup", message.from_user.id)

@router.message(Command("testupload"))
async def cmd_test_upload(message: Message):
    """Тестирование методов загрузки фотографий (только для администраторов)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    lang = user_settings.get('lang', 'ru')
    
    await message.answer(t(lang, 'admin.test_upload'))
    
    try:
        # Создаем тестовый предмет
        locations = await homebox_api.get_locations()
        if not locations:
            await message.answer("❌ Не удалось получить список локаций для тестирования")
            return
        
        # Создаем тестовый предмет
        test_item_result = await homebox_api.create_item(
            name="Test Upload Item",
            description="Test item for upload methods",
            location_id=str(locations[0]['id'])
        )
        
        if 'error' in test_item_result:
            await message.answer(f"❌ Ошибка создания тестового предмета: {test_item_result['error']}")
            return
        
        test_item_id = test_item_result.get('id')
        
        # Создаем тестовое изображение
        from PIL import Image
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # Создаем простое тестовое изображение
            img = Image.new('RGB', (100, 100), color='red')
            img.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Тестируем единственный метод загрузки
            success = await homebox_api.upload_photo(test_item_id, temp_path)
            results = {'upload_photo': success}
            if not success:
                results['upload_photo_error'] = homebox_api.last_error
            
            # Форматируем результаты
            results_text = ""
            for method, success in results.items():
                if not method.endswith('_error'):
                    status = "✅ Успешно" if success else "❌ Ошибка"
                    error_info = results.get(f"{method}_error", "")
                    results_text += f"**{method}**: {status}\n"
                    if error_info:
                        results_text += f"   Ошибка: {error_info[:100]}...\n"
            
            await message.answer(t(lang, 'admin.test_upload.results', results=results_text), parse_mode="Markdown")
            
        finally:
            # Удаляем временный файл
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        log_user_action("admin_test_upload", message.from_user.id, {"results": results})
        
    except Exception as e:
        await message.answer(f"❌ Ошибка тестирования: {str(e)}")
        log_error(e, "admin test upload", message.from_user.id)

@router.message(Command("checkapi"))
async def cmd_check_api(message: Message):
    """Проверка возможностей API HomeBox (только для администраторов)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    lang = user_settings.get('lang', 'ru')
    
    await message.answer(t(lang, 'admin.check_api'))
    
    try:
        # Проверяем возможности API
        api_info = await homebox_api.check_api_capabilities()
        
        # Форматируем результаты
        results_text = ""
        for endpoint, info in api_info.items():
            if 'data' in info:
                results_text += f"**{endpoint}**: ✅ Доступен\n"
                if isinstance(info['data'], dict):
                    for key, value in info['data'].items():
                        results_text += f"   {key}: {str(value)[:50]}...\n"
            elif 'status' in info:
                results_text += f"**{endpoint}**: HTTP {info['status']}\n"
            elif 'error' in info:
                results_text += f"**{endpoint}**: ❌ {info['error']}\n"
        
        if not results_text:
            results_text = "❌ Не удалось получить информацию об API"
        
        await message.answer(t(lang, 'admin.check_api.results', results=results_text), parse_mode="Markdown")
        
        log_user_action("admin_check_api", message.from_user.id, {"api_info": api_info})
        
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки API: {str(e)}")
        log_error(e, "admin check api", message.from_user.id)

@router.message(Command("quicktest"))
async def cmd_quick_test(message: Message):
    """Быстрый тест загрузки фотографий (только для администраторов)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    lang = user_settings.get('lang', 'ru')
    
    await message.answer(t(lang, 'admin.quick_test'))
    
    try:
        # Создаем тестовый предмет
        locations = await homebox_api.get_locations()
        if not locations:
            await message.answer("❌ Не удалось получить список локаций")
            return
        
        # Создаем тестовый предмет
        test_item_result = await homebox_api.create_item(
            name="Quick Test Item",
            description="Quick test item",
            location_id=str(locations[0]['id'])
        )
        
        if 'error' in test_item_result:
            await message.answer(f"❌ Ошибка создания тестового предмета: {test_item_result['error']}")
            return
        
        test_item_id = test_item_result.get('id')
        
        # Создаем тестовое изображение
        from PIL import Image
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # Создаем простое тестовое изображение
            img = Image.new('RGB', (50, 50), color='blue')
            img.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Тестируем единственный метод загрузки
            success = await homebox_api.upload_photo(test_item_id, temp_path)
            
            if success:
                await message.answer(t(lang, 'admin.quick_test.success'))
                log_user_action("admin_quick_test", message.from_user.id, {"success": True})
            else:
                await message.answer(t(lang, 'admin.quick_test.failed', error=homebox_api.last_error))
                log_user_action("admin_quick_test", message.from_user.id, {"success": False, "error": homebox_api.last_error})
            
        finally:
            # Удаляем временный файл
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        await message.answer(t(lang, 'admin.quick_test.failed', error=str(e)))
        log_error(e, "admin quick test", message.from_user.id)

@router.callback_query(F.data.in_({"lang_ru", "lang_en"}))
async def cb_set_lang(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.answer(t(lang, 'access.denied'), show_alert=True)
        return
    
    lang = 'ru' if callback.data == 'lang_ru' else 'en'
    settings = await db.get_user_settings(callback.from_user.id)
    settings['lang'] = lang
    await db.set_user_settings(callback.from_user.id, settings)
    
    text = t(lang, 'settings.lang.set.ru') if lang == 'ru' else t(lang, 'settings.lang.set.en')
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(lang))
    await callback.message.answer(text)
    await callback.answer()

def models_keyboard(current_model: str, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    models = config.AVAILABLE_MODELS
    start = page * page_size
    end = min(start + page_size, len(models))
    for m in models[start:end]:
        label = ("✓ " if m == current_model else "") + m
        builder.row(InlineKeyboardButton(text=label, callback_data=f"model_{m}"))
    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« Prev", callback_data=f"model_page_{page-1}"))
    if end < len(models):
        nav.append(InlineKeyboardButton(text="Next »", callback_data=f"model_page_{page+1}"))
    if nav:
        builder.row(*nav)
    return builder.as_markup()

@router.callback_query(F.data.startswith("model_page_"))
async def cb_model_page(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.answer(t(lang, 'access.denied'), show_alert=True)
        return
    
    try:
        page = int(callback.data.replace("model_page_", ""))
    except Exception:
        page = 0
    
    settings = await db.get_user_settings(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=models_keyboard(settings.get('model', config.DEFAULT_MODEL), page))
    await callback.answer()

@router.callback_query(F.data.startswith("model_"))
async def cb_set_model(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.answer(t(lang, 'access.denied'), show_alert=True)
        return
    
    model = callback.data.replace("model_", "")
    if model not in config.AVAILABLE_MODELS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.answer(t(lang, 'settings.model.unavailable'), show_alert=True)
        return
    
    settings = await db.get_user_settings(callback.from_user.id)
    settings['model'] = model
    await db.set_user_settings(callback.from_user.id, settings)
    
    await callback.message.edit_reply_markup(reply_markup=models_keyboard(model, 0))
    await callback.message.answer(f"Модель установлена: {model}")
    await callback.answer()

def create_confirmation_keyboard(locations: list, current_location: str) -> InlineKeyboardMarkup:
    """Создание клавиатуры для подтверждения"""
    builder = InlineKeyboardBuilder()
    user_lang = None
    # Try to infer language from locations/current session would require user id; keep RU labels defaulted later
    builder.row(
        InlineKeyboardButton(text=t('ru', 'btn.edit.name'), callback_data="edit_name")
    )
    builder.row(
        InlineKeyboardButton(text=t('ru', 'btn.edit.description'), callback_data="edit_description")
    )
    builder.row(
        InlineKeyboardButton(text=t('ru', 'btn.edit.location'), callback_data="edit_location")
    )
    builder.row(
        InlineKeyboardButton(text=t('ru', 'btn.confirm'), callback_data="confirm")
    )
    builder.row(
        InlineKeyboardButton(text=t('ru', 'btn.cancel'), callback_data="cancel")
    )
    
    return builder.as_markup()

def create_locations_keyboard(locations: list) -> InlineKeyboardMarkup:
    """Создание клавиатуры выбора локации"""
    builder = InlineKeyboardBuilder()
    
    for loc in locations:
        builder.row(
            InlineKeyboardButton(
                text=loc['name'],
                callback_data=f"location_{loc['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text=t('ru', 'back'), callback_data="back_to_confirm")
    )
    
    return builder.as_markup()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    try:
        log_user_action("start_command", message.from_user.id, {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name
        })
        
        # Проверяем авторизацию пользователя
        if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
            user_settings = await db.get_user_settings(message.from_user.id)
            lang = user_settings.get('lang', 'ru')
            await message.answer(t(lang, 'access.denied'))
            log_user_action("access_denied", message.from_user.id)
            return
            
        await state.clear()
        
        # Получаем или создаем настройки пользователя
        user_settings = await db.get_user_settings(message.from_user.id)
        if not user_settings or user_settings == {'lang': 'ru', 'model': 'gpt-4o'}:
            # Новый пользователь
            await db.set_user_settings(message.from_user.id, {
                'lang': 'ru',
                'model': config.DEFAULT_MODEL
            })
            log_user_action("first_time_user", message.from_user.id)
        
        # Обновляем статистику
        await db.add_user(message.from_user.id)
        await db.increment_requests()
            
        lang = user_settings.get('lang', 'ru')
        await message.answer(t(lang, 'start.intro'))
        await state.set_state(ItemStates.waiting_for_photo)
        
    except Exception as e:
        log_error(e, "start command handler", message.from_user.id)
        await message.answer("Произошла ошибка. Попробуйте еще раз.")

@router.message(ItemStates.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Обработчик получения фотографии"""
    try:
        log_user_action("photo_received", message.from_user.id, {
            "caption": message.caption,
            "photo_size": len(message.photo) if message.photo else 0
        })
        
        # Обновляем статистику
        await db.increment_requests()
        
        if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
            user_settings = await db.get_user_settings(message.from_user.id)
            lang = user_settings.get('lang', 'ru')
            await message.answer(t(lang, 'access.denied'))
            return
            
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        
        # Отправляем начальный индикатор загрузки
        progress_msg = await message.answer(t(lang, 'progress.downloading'))
        
        # Получаем фото в максимальном качестве
        photo = message.photo[-1]
        
        # Скачиваем фото
        file = await bot.get_file(photo.file_id)
        file_path = f"temp_{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        await bot.download_file(file.file_path, file_path)
        
        # Обновляем прогресс - валидация
        progress_msg = await update_progress_message(message, progress_msg, 'validating', lang)
        
        # Валидируем скачанное изображение
        is_valid, error_msg = validate_image_file(file_path)
        if not is_valid:
            # Удаляем невалидный файл
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await progress_msg.delete()
            await message.answer(
                f"{t(lang, 'error.invalid_image', error=error_msg)}\n\n"
                f"{t(lang, 'error.try_again')}"
            )
            return
        
        # Обновляем прогресс - получение локаций
        progress_msg = await update_progress_message(message, progress_msg, 'getting_locations', lang)
        
        # Получаем локации из Homebox
        locations = await homebox_api.get_locations()
        
        if not locations:
            # Удаляем временный файл
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await progress_msg.delete()
            # Покажем диагностическую информацию, если доступна
            diagnostic = getattr(homebox_api, 'last_error', None)
            if diagnostic:
                await message.answer(
                    f"{t(lang, 'homebox.locations.fail')}\n\n"
                    f"Подробности: {diagnostic}"
                )
            else:
                await message.answer(t(lang, 'homebox.locations.fail'))
            await state.clear()
            return
        
        # Обновляем прогресс - анализ ИИ
        progress_msg = await update_progress_message(message, progress_msg, 'analyzing', lang)
        
        # Анализируем изображение
        model = user_settings.get('model', config.DEFAULT_MODEL)
        
        # Извлекаем caption (описание фото), если есть
        caption = message.caption if message.caption else None
        
        analysis = await analyze_image(file_path, locations, lang, model, caption)
        
        # Находим ID предложенной локации
        suggested_location_id = None
        for loc in locations:
            if loc['name'] == analysis['suggested_location']:
                suggested_location_id = str(loc['id'])
                break
        
        if not suggested_location_id:
            suggested_location_id = str(locations[0]['id'])
            analysis['suggested_location'] = locations[0]['name']
        
        # Сохраняем данные
        items_data[message.from_user.id] = {
            'name': analysis['name'],
            'description': analysis['description'],
            'location_id': suggested_location_id,
            'location_name': analysis['suggested_location'],
            'photo_path': file_path,
            'photo_file_id': photo.file_id,
            'locations': locations,
            'progress_msg_id': progress_msg.message_id
        }
        
        # Формируем сообщение с информацией о caption
        caption_info = ""
        if caption and caption.strip():
            caption_info = t(lang, 'caption.used') + "\n\n"
        else:
            caption_info = t(lang, 'caption.not_used') + "\n\n"
        
        # Удаляем сообщение о прогрессе
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        # Отправляем результат
        await message.answer_photo(
            photo=photo.file_id,
            caption=(
                t(lang, 'result.title')
                + caption_info
                + t(lang, 'field.name', value=analysis['name']) + "\n\n"
                + t(lang, 'field.description', value=analysis['description']) + "\n\n"
                + t(lang, 'field.location', value=analysis['suggested_location']) + "\n\n"
                + t(lang, 'edit.what_change')
            ),
            reply_markup=create_confirmation_keyboard(locations, analysis['suggested_location']),
            parse_mode="Markdown"
        )
        
        await state.set_state(ItemStates.confirming_data)
        log_user_action("photo_analyzed", message.from_user.id, {
            "analysis_result": analysis,
            "model_used": model
        })
        
    except Exception as e:
        log_error(e, "photo handling", message.from_user.id)
        
        # Очищаем временные файлы при ошибке
        temp_files = [f for f in os.listdir('.') if f.startswith(f'temp_{message.from_user.id}_')]
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception:
                pass
        
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(
            "Произошла ошибка при обработке фотографии. Попробуйте еще раз или отправьте другое фото."
        )

@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    """Edit item name"""
    # Remove buttons from the previous message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    user_settings = await db.get_user_settings(callback.from_user.id)
    lang = user_settings.get('lang', 'ru')
    await callback.message.answer(t(lang, 'edit.enter_name'))
    await state.set_state(ItemStates.editing_name)
    await callback.answer()

@router.message(ItemStates.editing_name)
async def save_new_name(message: Message, state: FSMContext):
    """Сохранение нового названия"""
    user_data = items_data.get(message.from_user.id)
    if user_data:
        user_data['name'] = message.text
        
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(
            f"{t(lang, 'changed.name')}\n\n"
            f"{t(lang, 'field.name', value=user_data['name'])}\n"
            f"{t(lang, 'field.description', value=user_data['description'])}\n"
            f"**Ящик:** {user_data['location_name']}",
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name']
            ),
            parse_mode="Markdown"
        )
        await state.set_state(ItemStates.confirming_data)

@router.callback_query(F.data == "edit_description")
async def edit_description(callback: CallbackQuery, state: FSMContext):
    """Edit item description"""
    # Remove buttons from the previous message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    user_settings = await db.get_user_settings(callback.from_user.id)
    lang = user_settings.get('lang', 'ru')
    await callback.message.answer(t(lang, 'edit.enter_description'))
    await state.set_state(ItemStates.editing_description)
    await callback.answer()

@router.message(ItemStates.editing_description)
async def save_new_description(message: Message, state: FSMContext):
    """Сохранение нового описания"""
    user_data = items_data.get(message.from_user.id)
    if user_data:
        user_data['description'] = message.text
        
        user_settings = await db.get_user_settings(message.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await message.answer(
            f"{t(lang, 'changed.description')}\n\n"
            f"{t(lang, 'field.name', value=user_data['name'])}\n"
            f"{t(lang, 'field.description', value=user_data['description'])}\n"
            f"**Ящик:** {user_data['location_name']}",
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name']
            ),
            parse_mode="Markdown"
        )
        await state.set_state(ItemStates.confirming_data)

@router.callback_query(F.data == "edit_location")
async def edit_location(callback: CallbackQuery, state: FSMContext):
    """Select a new location"""
    user_data = items_data.get(callback.from_user.id)
    if user_data:
        # Remove buttons from the previous (confirmation) message
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.message.answer(
            t(lang, 'edit.select_location'),
            reply_markup=create_locations_keyboard(user_data['locations'])
        )
        await state.set_state(ItemStates.selecting_location)
    await callback.answer()

@router.callback_query(F.data.startswith("location_"))
async def save_new_location(callback: CallbackQuery, state: FSMContext):
    """Save new location selection"""
    location_id = callback.data.replace("location_", "")
    user_data = items_data.get(callback.from_user.id)
    
    if user_data:
        # Remove location picker buttons
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        # Находим название локации
        location_name = None
        for loc in user_data['locations']:
            if str(loc['id']) == str(location_id):
                location_name = loc['name']
                break
        
        user_data['location_id'] = str(location_id)
        user_data['location_name'] = location_name
        
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.message.answer(
            f"{t(lang, 'changed.location')}\n\n"
            f"{t(lang, 'field.name', value=user_data['name'])}\n"
            f"{t(lang, 'field.description', value=user_data['description'])}\n"
            f"**Ящик:** {user_data['location_name']}",
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name']
            ),
            parse_mode="Markdown"
        )
        await state.set_state(ItemStates.confirming_data)
    await callback.answer()

@router.callback_query(F.data == "back_to_confirm")
async def back_to_confirm(callback: CallbackQuery, state: FSMContext):
    """Return to confirmation screen"""
    user_data = items_data.get(callback.from_user.id)
    if user_data:
        # Remove location picker buttons
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        user_settings = await db.get_user_settings(callback.from_user.id)
        lang = user_settings.get('lang', 'ru')
        await callback.message.answer(
            f"{t(lang, 'field.name', value=user_data['name'])}\n"
            f"{t(lang, 'field.description', value=user_data['description'])}\n"
            f"**Ящик:** {user_data['location_name']}",
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name']
            ),
            parse_mode="Markdown"
        )
        await state.set_state(ItemStates.confirming_data)
    await callback.answer()

@router.callback_query(F.data == "confirm")
async def confirm_and_add(callback: CallbackQuery, state: FSMContext):
    """Confirm and create item in HomeBox"""
    # Remove confirmation buttons
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    user_settings = await db.get_user_settings(callback.from_user.id)
    lang = user_settings.get('lang', 'ru')
    
    # Отправляем индикатор загрузки
    progress_msg = await callback.message.answer(t(lang, 'progress.uploading'))
    
    user_data = items_data.get(callback.from_user.id)
    if user_data:
        # Убедимся, что локальный файл существует. Если нет — попробуем скачать заново по file_id
        try:
            photo_path = user_data.get('photo_path')
            photo_file_id = user_data.get('photo_file_id')
            if (not photo_path) or (not os.path.exists(photo_path)):
                if photo_file_id:
                    file = await bot.get_file(photo_file_id)
                    # Восстановим путь, если отсутствует
                    if not photo_path:
                        photo_path = f"temp_{callback.from_user.id}.jpg"
                        user_data['photo_path'] = photo_path
                    await bot.download_file(file.file_path, photo_path)
        except Exception as _:
            # Игнорируем, Homebox сохранит без фото, но мы не падаем
            pass
        result = await homebox_api.create_item(
            name=user_data['name'],
            description=user_data['description'],
            location_id=user_data['location_id'],
            photo_path=user_data['photo_path']
        )
        
        # Удаляем индикатор прогресса
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        if 'error' not in result:
            await callback.message.answer(
                f"{t(lang, 'added.success')}\n\n"
                f"{t(lang, 'field.name', value=user_data['name'])}\n"
                f"**Ящик:** {user_data['location_name']}\n\n"
                f"{t(lang, 'added.new_prompt')}\n"
                f"{(t(lang, 'added.photo_failed') if result.get('photo_upload') == 'failed' else '')}",
                parse_mode="Markdown"
            )
            if result.get('photo_upload') == 'failed':
                diagnostic = getattr(homebox_api, 'last_error', None)
                if diagnostic:
                    await callback.message.answer(
                        f"Подробности загрузки фото: {diagnostic}"
                    )
            
            # Удаляем временный файл
            if os.path.exists(user_data['photo_path']):
                os.remove(user_data['photo_path'])
            
            # Очищаем данные
            del items_data[callback.from_user.id]
            # Обновляем статистику
            await db.increment_items_processed()
            await state.set_state(ItemStates.waiting_for_photo)
        else:
            await callback.message.answer(t(lang, 'added.fail'))
    
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_operation(callback: CallbackQuery, state: FSMContext):
    """Cancel current operation"""
    # Remove any buttons on the previous message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    user_data = items_data.get(callback.from_user.id)
    if user_data and os.path.exists(user_data.get('photo_path', '')):
        os.remove(user_data['photo_path'])
    
    if callback.from_user.id in items_data:
        del items_data[callback.from_user.id]
    
    user_settings = await db.get_user_settings(callback.from_user.id)
    lang = user_settings.get('lang', 'ru')
    await callback.message.answer(t(lang, 'cancel.done'))
    await state.set_state(ItemStates.waiting_for_photo)
    await callback.answer()

async def main():
    dp.include_router(router)
    
    # Инициализируем HomeBox API с контекстным менеджером
    async with homebox_api:
        logger.info("Starting bot...")
        await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        log_error(e, "main function")
        logger.error("Bot crashed")
