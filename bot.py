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
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logging
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
    """Check if user is administrator"""
    return user_id in config.ALLOWED_USER_IDS

def is_location_bot_allowed(location: dict) -> bool:
    """Check if location is allowed for bot usage based on marker in description"""
    filter_mode = config.LOCATION_FILTER_MODE
    
    # If filter mode is 'none', no locations are allowed
    if filter_mode == 'none':
        return False
    
    # If filter mode is 'all', all locations are allowed
    if filter_mode == 'all':
        return True
    
    # If filter mode is 'marker', check for marker in description
    if filter_mode == 'marker':
        description = location.get('description', '')
        marker = config.LOCATION_MARKER
        return marker in description
    
    # Default: no locations allowed
    return False

def filter_allowed_locations(locations: list) -> list:
    """Filter locations based on bot allowance"""
    return [loc for loc in locations if is_location_bot_allowed(loc)]

async def get_uptime() -> str:
    """Return bot uptime in readable format"""
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
    """Clean up temporary files"""
    temp_files = [f for f in os.listdir('.') if f.startswith('temp_')]
    removed_count = 0
    
    for temp_file in temp_files:
        try:
            # Check file age (older than 1 hour)
            file_time = datetime.fromtimestamp(os.path.getmtime(temp_file))
            if datetime.now() - file_time > timedelta(hours=1):
                os.remove(temp_file)
                removed_count += 1
        except Exception as e:
            logger.error(f"Error removing temp file {temp_file}: {e}")
    
    return removed_count

def create_progress_bar(step: int, total: int = 5, bot_lang: str = 'ru') -> str:
    """Create a visual progress bar with emoji indicators"""
    progress_chars = ['⬜', '🟨', '🟧', '🟩', '✅']
    filled = min(step, total)
    bar = ''.join([progress_chars[min(i, len(progress_chars)-1)] for i in range(total)])
    return f"{bar} {filled}/{total}"

async def update_progress_message(message: Message, progress_msg: Message, step: str, bot_lang: str, step_num: int = 1):
    """Update progress message with visual indicator"""
    progress_bar = create_progress_bar(step_num)
    progress_text = f"{progress_bar}\n\n{t(bot_lang, f'progress.{step}')}"
    
    try:
        await progress_msg.edit_text(progress_text)
    except Exception as e:
        logger.warning(f"Failed to update progress message: {e}")
        # If update failed, send a new message
        try:
            await progress_msg.delete()
        except:
            pass
        return await message.answer(progress_text)
    return progress_msg

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def analyze_image(image_path: str, locations: list, lang: str = 'ru', model: str | None = None, caption: str | None = None) -> dict:
    """Analyze image via OpenAI Vision to extract item metadata."""
    base64_image = encode_image(image_path)
    
    locations_text = "\n".join([f"- {loc['name']}" for loc in locations])
    
    # Add caption information to prompt if available
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
        # Use selected model or default
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

def bot_lang_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    """Create bot interface language selection keyboard"""
    builder = InlineKeyboardBuilder()
    ru_label = t(current_lang, 'settings.lang.ru') + (" ✓" if current_lang == 'ru' else "")
    en_label = t(current_lang, 'settings.lang.en') + (" ✓" if current_lang == 'en' else "")
    builder.row(InlineKeyboardButton(text=ru_label, callback_data="bot_lang_ru"))
    builder.row(InlineKeyboardButton(text=en_label, callback_data="bot_lang_en"))
    return builder.as_markup()

def gen_lang_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    """Create generation language selection keyboard"""
    builder = InlineKeyboardBuilder()
    ru_label = t(current_lang, 'settings.lang.ru') + (" ✓" if current_lang == 'ru' else "")
    en_label = t(current_lang, 'settings.lang.en') + (" ✓" if current_lang == 'en' else "")
    builder.row(InlineKeyboardButton(text=ru_label, callback_data="gen_lang_ru"))
    builder.row(InlineKeyboardButton(text=en_label, callback_data="gen_lang_en"))
    return builder.as_markup()

def settings_main_keyboard(bot_lang: str) -> InlineKeyboardMarkup:
    """Create main settings keyboard with improved design"""
    builder = InlineKeyboardBuilder()
    
    # First row - languages
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'settings.bot_lang.title'), callback_data="settings_bot_lang"),
        InlineKeyboardButton(text=t(bot_lang, 'settings.gen_lang.title'), callback_data="settings_gen_lang")
    )
    
    # Second row - model
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'settings.choose_model'), callback_data="settings_model")
    )
    
    # Third row - quick actions
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="quick_stats"),
        InlineKeyboardButton(text="🔄 Перезапуск", callback_data="quick_restart")
    )
    
    return builder.as_markup()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'access.denied'))
        return
    
    settings = await db.get_user_settings(message.from_user.id)
    bot_lang = settings.get('bot_lang', 'ru')
    await message.answer(
        t(bot_lang, 'settings.title'),
        reply_markup=settings_main_keyboard(bot_lang)
    )

@router.message(Command(commands=["myid", "id"]))
async def cmd_myid(message: Message):
    """Send user their Telegram ID (available to everyone)."""
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    await message.answer(t(bot_lang, 'cmd.myid', user_id=message.from_user.id))

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show bot statistics (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    stats = await db.get_bot_stats()
    
    stats_text = (
        f"**{t(bot_lang, 'admin.stats.title')}**\n\n"
        f"👥 {t(bot_lang, 'admin.stats.users', count=len(stats.get('users_registered', [])))}\n"
        f"📦 {t(bot_lang, 'admin.stats.items', count=stats.get('items_processed', 0))}\n"
        f"🔄 {t(bot_lang, 'admin.stats.sessions', count=len(items_data))}\n"
        f"⏱️ {t(bot_lang, 'admin.stats.uptime', uptime=await get_uptime())}\n\n"
        f"📈 Всего запросов: {stats.get('total_requests', 0)}"
    )
    
    await message.answer(stats_text, parse_mode="Markdown")

@router.message(Command("cleanup"))
async def cmd_cleanup(message: Message):
    """Clean up temporary files (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    try:
        removed_count = await cleanup_temp_files()
        await message.answer(t(bot_lang, 'admin.cleanup.done', files=removed_count))
        log_user_action("admin_cleanup", message.from_user.id, {"files_removed": removed_count})
    except Exception as e:
        await message.answer(t(bot_lang, 'admin.cleanup.error', error=str(e)))
        log_error(e, "admin cleanup", message.from_user.id)

@router.message(Command("testupload"))
async def cmd_test_upload(message: Message):
    """Test photo upload methods (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    await message.answer(t(bot_lang, 'admin.test_upload'))
    
    try:
        # Create test item
        locations = await homebox_api.get_locations()
        if not locations:
            await message.answer("❌ Не удалось получить список локаций для тестирования")
            return
        
        # Create test item
        test_item_result = await homebox_api.create_item(
            name="Test Upload Item",
            description="Test item for upload methods",
            location_id=str(locations[0]['id'])
        )
        
        if 'error' in test_item_result:
            await message.answer(f"❌ Ошибка создания тестового предмета: {test_item_result['error']}")
            return
        
        test_item_id = test_item_result.get('id')
        
        # Create test image
        from PIL import Image
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # Create simple test image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Test the only upload method
            success = await homebox_api.upload_photo(test_item_id, temp_path)
            results = {'upload_photo': success}
            if not success:
                results['upload_photo_error'] = homebox_api.last_error
            
            # Format results
            results_text = ""
            for method, success in results.items():
                if not method.endswith('_error'):
                    status = "✅ Успешно" if success else "❌ Ошибка"
                    error_info = results.get(f"{method}_error", "")
                    results_text += f"**{method}**: {status}\n"
                    if error_info:
                        results_text += f"   Ошибка: {error_info[:100]}...\n"
            
            await message.answer(t(bot_lang, 'admin.test_upload.results', results=results_text), parse_mode="Markdown")
            
        finally:
            # Remove temporary file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        log_user_action("admin_test_upload", message.from_user.id, {"results": results})
        
    except Exception as e:
        await message.answer(f"❌ Ошибка тестирования: {str(e)}")
        log_error(e, "admin test upload", message.from_user.id)

@router.message(Command("checkapi"))
async def cmd_check_api(message: Message):
    """Check HomeBox API capabilities (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    await message.answer(t(bot_lang, 'admin.check_api'))
    
    try:
        # Check API capabilities
        api_info = await homebox_api.check_api_capabilities()
        
        # Format results
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
        
        await message.answer(t(bot_lang, 'admin.check_api.results', results=results_text), parse_mode="Markdown")
        
        log_user_action("admin_check_api", message.from_user.id, {"api_info": api_info})
        
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки API: {str(e)}")
        log_error(e, "admin check api", message.from_user.id)

@router.message(Command("quicktest"))
async def cmd_quick_test(message: Message):
    """Quick photo upload test (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    await message.answer(t(bot_lang, 'admin.quick_test'))
    
    try:
        # Create test item
        locations = await homebox_api.get_locations()
        if not locations:
            await message.answer("❌ Не удалось получить список локаций")
            return
        
        # Create test item
        test_item_result = await homebox_api.create_item(
            name="Quick Test Item",
            description="Quick test item",
            location_id=str(locations[0]['id'])
        )
        
        if 'error' in test_item_result:
            await message.answer(f"❌ Ошибка создания тестового предмета: {test_item_result['error']}")
            return
        
        test_item_id = test_item_result.get('id')
        
        # Create test image
        from PIL import Image
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # Create simple test image
            img = Image.new('RGB', (50, 50), color='blue')
            img.save(temp_file.name, 'JPEG')
            temp_path = temp_file.name
        
        try:
            # Test the only upload method
            success = await homebox_api.upload_photo(test_item_id, temp_path)
            
            if success:
                await message.answer(t(bot_lang, 'admin.quick_test.success'))
                log_user_action("admin_quick_test", message.from_user.id, {"success": True})
            else:
                await message.answer(t(bot_lang, 'admin.quick_test.failed', error=homebox_api.last_error))
                log_user_action("admin_quick_test", message.from_user.id, {"success": False, "error": homebox_api.last_error})
            
        finally:
            # Remove temporary file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        await message.answer(t(bot_lang, 'admin.quick_test.failed', error=str(e)))
        log_error(e, "admin quick test", message.from_user.id)

@router.message(Command("locations"))
async def cmd_locations(message: Message):
    """Show location management commands (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    help_text = (
        f"🏠 **Location Management Commands**\n\n"
        f"📋 `/list_locations` - Show all available locations\n"
        f"✅ `/allowed_locations` - Show allowed locations for bot\n"
        f"⚙️ `/location_config` - Show current location configuration\n\n"
        f"💡 **Current marker:** `{config.LOCATION_MARKER}`\n"
        f"🔧 **Filter mode:** `{config.LOCATION_FILTER_MODE}`"
    )
    
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("list_locations"))
async def cmd_list_locations(message: Message):
    """List all available locations with bot access status (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    try:
        all_locations = await homebox_api.get_locations()
        allowed_locations = filter_allowed_locations(all_locations)
        
        if not all_locations:
            await message.answer("❌ Не удалось получить список локаций")
            return
        
        locations_text = f"🏠 **All Available Locations:**\n\n"
        for loc in all_locations:
            status = "✅" if is_location_bot_allowed(loc) else "❌"
            description = loc.get('description', 'No description')
            marker_status = "🎯" if config.LOCATION_MARKER in description else "⚪"
            locations_text += f"{status} {marker_status} **{loc['name']}** (ID: {loc['id']})\n"
            if description and len(description) > 0:
                locations_text += f"    📝 {description[:50]}{'...' if len(description) > 50 else ''}\n"
        
        locations_text += f"\n📊 **Statistics:**\n"
        locations_text += f"📦 **Total locations:** {len(all_locations)}\n"
        locations_text += f"✅ **Bot allowed:** {len(allowed_locations)}\n"
        locations_text += f"❌ **Bot blocked:** {len(all_locations) - len(allowed_locations)}\n"
        locations_text += f"🎯 **With marker:** {sum(1 for loc in all_locations if config.LOCATION_MARKER in loc.get('description', ''))}"
        
        await message.answer(locations_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения локаций: {str(e)}")
        log_error(e, "list locations", message.from_user.id)

@router.message(Command("allowed_locations"))
async def cmd_allowed_locations(message: Message):
    """Show allowed locations for bot (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    try:
        all_locations = await homebox_api.get_locations()
        allowed_locations = filter_allowed_locations(all_locations)
        
        if not allowed_locations:
            await message.answer(
                f"❌ **Нет разрешенных локаций**\n\n"
                f"Все локации заблокированы для бота.\n\n"
                f"💡 **Для разрешения добавьте маркер `{config.LOCATION_MARKER}` в описание нужных локаций в HomeBox.**"
            )
            return
        
        locations_text = f"✅ **Allowed Locations for Bot:**\n\n"
        for loc in allowed_locations:
            description = loc.get('description', 'No description')
            locations_text += f"📦 **{loc['name']}** (ID: {loc['id']})\n"
            locations_text += f"    📝 {description}\n\n"
        
        locations_text += f"📊 **Total allowed:** {len(allowed_locations)} locations"
        
        await message.answer(locations_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения разрешенных локаций: {str(e)}")
        log_error(e, "allowed locations", message.from_user.id)

@router.message(Command("location_config"))
async def cmd_location_config(message: Message):
    """Show current location configuration (admin only)."""
    if not is_admin(message.from_user.id):
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'admin.access.denied'))
        return
    
    try:
        config_text = f"⚙️ **Location Configuration:**\n\n"
        config_text += f"🔧 **Filter Mode:** `{config.LOCATION_FILTER_MODE}`\n"
        config_text += f"🎯 **Marker:** `{config.LOCATION_MARKER}`\n\n"
        
        config_text += f"📋 **Available Modes:**\n"
        config_text += f"• `marker` - Only locations with marker in description\n"
        config_text += f"• `all` - All locations allowed\n"
        config_text += f"• `none` - No locations allowed\n\n"
        
        config_text += f"💡 **How to enable locations:**\n"
        config_text += f"Add `{config.LOCATION_MARKER}` to the description of desired locations in HomeBox."
        
        await message.answer(config_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения конфигурации: {str(e)}")
        log_error(e, "location config", message.from_user.id)

@router.callback_query(F.data == "settings_bot_lang")
async def cb_settings_bot_lang(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    settings = await db.get_user_settings(callback.from_user.id)
    bot_lang = settings.get('bot_lang', 'ru')
    await callback.message.edit_text(
        t(bot_lang, 'settings.bot_lang.title'),
        reply_markup=bot_lang_keyboard(bot_lang)
    )
    await callback.answer()

@router.callback_query(F.data == "settings_gen_lang")
async def cb_settings_gen_lang(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    settings = await db.get_user_settings(callback.from_user.id)
    bot_lang = settings.get('bot_lang', 'ru')
    await callback.message.edit_text(
        t(bot_lang, 'settings.gen_lang.title'),
        reply_markup=gen_lang_keyboard(settings.get('gen_lang', 'ru'))
    )
    await callback.answer()

@router.callback_query(F.data == "settings_model")
async def cb_settings_model(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    settings = await db.get_user_settings(callback.from_user.id)
    bot_lang = settings.get('bot_lang', 'ru')
    await callback.message.edit_text(
        t(bot_lang, 'settings.choose_model'),
        reply_markup=models_keyboard(settings.get('model', config.DEFAULT_MODEL), bot_lang, 0)
    )
    await callback.answer()

@router.callback_query(F.data.in_({"bot_lang_ru", "bot_lang_en"}))
async def cb_set_bot_lang(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    lang = 'ru' if callback.data == 'bot_lang_ru' else 'en'
    settings = await db.get_user_settings(callback.from_user.id)
    settings['bot_lang'] = lang
    await db.set_user_settings(callback.from_user.id, settings)
    
    text = t(lang, 'settings.bot_lang.set.ru') if lang == 'ru' else t(lang, 'settings.bot_lang.set.en')
    await callback.message.edit_reply_markup(reply_markup=bot_lang_keyboard(lang))
    await callback.message.answer(text)
    await callback.answer(f"🌐 Язык изменен на {lang.upper()}", show_alert=True)

@router.callback_query(F.data.in_({"gen_lang_ru", "gen_lang_en"}))
async def cb_set_gen_lang(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    lang = 'ru' if callback.data == 'gen_lang_ru' else 'en'
    settings = await db.get_user_settings(callback.from_user.id)
    settings['gen_lang'] = lang
    await db.set_user_settings(callback.from_user.id, settings)
    
    bot_lang = settings.get('bot_lang', 'ru')
    text = t(bot_lang, 'settings.gen_lang.set.ru') if lang == 'ru' else t(bot_lang, 'settings.gen_lang.set.en')
    await callback.message.edit_reply_markup(reply_markup=gen_lang_keyboard(lang))
    await callback.message.answer(text)
    await callback.answer(f"🤖 Язык генерации: {lang.upper()}", show_alert=True)

def models_keyboard(current_model: str, lang: str = 'ru', page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    models = config.AVAILABLE_MODELS
    start = page * page_size
    end = min(start + page_size, len(models))
    for m in models[start:end]:
        label = ("✓ " if m == current_model else "") + m
        builder.row(InlineKeyboardButton(text=label, callback_data=f"model_{m}"))
    # Navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, 'btn.prev'), callback_data=f"model_page_{page-1}"))
    if end < len(models):
        nav.append(InlineKeyboardButton(text=t(lang, 'btn.next'), callback_data=f"model_page_{page+1}"))
    if nav:
        builder.row(*nav)
    return builder.as_markup()

@router.callback_query(F.data.startswith("model_page_"))
async def cb_model_page(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    try:
        page = int(callback.data.replace("model_page_", ""))
    except Exception:
        page = 0
    
    settings = await db.get_user_settings(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=models_keyboard(settings.get('model', config.DEFAULT_MODEL), settings.get('lang', 'ru'), page))
    await callback.answer()

@router.callback_query(F.data.startswith("model_"))
async def cb_set_model(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'access.denied'), show_alert=True)
        return
    
    model = callback.data.replace("model_", "")
    if model not in config.AVAILABLE_MODELS:
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.answer(t(bot_lang, 'settings.model.unavailable'), show_alert=True)
        return
    
    settings = await db.get_user_settings(callback.from_user.id)
    settings['model'] = model
    await db.set_user_settings(callback.from_user.id, settings)
    
    settings = await db.get_user_settings(callback.from_user.id)
    bot_lang = settings.get('bot_lang', 'ru')
    await callback.message.edit_reply_markup(reply_markup=models_keyboard(model, bot_lang, 0))
    await callback.message.answer(t(bot_lang, 'model.selected', model=model))
    await callback.answer(f"🧠 Модель: {model}", show_alert=True)

def create_confirmation_keyboard(locations: list, current_location: str, bot_lang: str = 'ru') -> InlineKeyboardMarkup:
    """Create confirmation keyboard with improved design"""
    builder = InlineKeyboardBuilder()
    
    # First row - edit name
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'btn.edit.name'), callback_data="edit_name")
    )
    
    # Second row - edit description
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'btn.edit.description'), callback_data="edit_description")
    )
    
    # Third row - edit location
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'btn.edit.location'), callback_data="edit_location")
    )
    
    # Fourth row - main actions
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'btn.confirm'), callback_data="confirm"),
        InlineKeyboardButton(text=t(bot_lang, 'btn.cancel'), callback_data="cancel")
    )
    
    return builder.as_markup()

def create_locations_keyboard(locations: list, bot_lang: str = 'ru') -> InlineKeyboardMarkup:
    """Create location selection keyboard with improved design"""
    builder = InlineKeyboardBuilder()
    
    # Add locations 2 per row for compactness
    for i in range(0, len(locations), 2):
        row_buttons = []
        for j in range(2):
            if i + j < len(locations):
                loc = locations[i + j]
                row_buttons.append(
                    InlineKeyboardButton(
                        text=loc['name'],
                        callback_data=f"location_{loc['id']}"
                    )
                )
        if row_buttons:
            builder.row(*row_buttons)
    
    # Back button
    builder.row(
        InlineKeyboardButton(text=t(bot_lang, 'back'), callback_data="back_to_confirm")
    )
    
    return builder.as_markup()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    try:
        log_user_action("start_command", message.from_user.id, {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name
        })
        
        # Check user authorization
        if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
            user_settings = await db.get_user_settings(message.from_user.id)
            bot_lang = user_settings.get('bot_lang', 'ru')
            await message.answer(t(bot_lang, 'access.denied'))
            log_user_action("access_denied", message.from_user.id)
            return
            
        await state.clear()
        
        # Get or create user settings
        user_settings = await db.get_user_settings(message.from_user.id)
        if not user_settings or user_settings == {'lang': 'ru', 'model': 'gpt-4o'}:
            # New user
            await db.set_user_settings(message.from_user.id, {
                'lang': 'ru',
                'model': config.DEFAULT_MODEL
            })
            log_user_action("first_time_user", message.from_user.id)
        
        # Update statistics
        await db.add_user(message.from_user.id)
        await db.increment_requests()
            
        bot_lang = user_settings.get('bot_lang', 'ru')
        await message.answer(t(bot_lang, 'start.intro'))
        await state.set_state(ItemStates.waiting_for_photo)
        
    except Exception as e:
        log_error(e, "start command handler", message.from_user.id)
        await message.answer("Произошла ошибка. Попробуйте еще раз.")

@router.message(ItemStates.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Handle photo upload"""
    try:
        log_user_action("photo_received", message.from_user.id, {
            "caption": message.caption,
            "photo_size": len(message.photo) if message.photo else 0
        })
        
        # Update statistics
        await db.increment_requests()
        
        if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
            user_settings = await db.get_user_settings(message.from_user.id)
            bot_lang = user_settings.get('bot_lang', 'ru')
            await message.answer(t(bot_lang, 'access.denied'))
            return
            
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        
        # Send initial loading indicator
        progress_msg = await message.answer(t(bot_lang, 'progress.downloading'))
        
        # Get photo in maximum quality
        photo = message.photo[-1]
        
        # Download photo
        file = await bot.get_file(photo.file_id)
        file_path = f"temp_{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        await bot.download_file(file.file_path, file_path)
        
        # Update progress - validation
        progress_msg = await update_progress_message(message, progress_msg, 'validating', bot_lang, 2)
        
        # Validate downloaded image
        is_valid, error_msg = validate_image_file(file_path)
        if not is_valid:
            # Remove invalid file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await progress_msg.delete()
            await message.answer(
                f"{t(bot_lang, 'error.invalid_image', error=error_msg)}\n\n"
                f"{t(bot_lang, 'error.try_again')}"
            )
            return
        
        # Update progress - getting locations
        progress_msg = await update_progress_message(message, progress_msg, 'getting_locations', bot_lang, 3)
        
        # Get locations from Homebox
        all_locations = await homebox_api.get_locations()
        
        if not all_locations:
            # Remove temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await progress_msg.delete()
            # Show diagnostic information if available
            diagnostic = getattr(homebox_api, 'last_error', None)
            if diagnostic:
                await message.answer(
                    f"{t(bot_lang, 'homebox.locations.fail')}\n\n"
                    f"Подробности: {diagnostic}"
                )
            else:
                await message.answer(t(bot_lang, 'homebox.locations.fail'))
            await state.clear()
            return
        
        # Filter locations based on bot allowance
        locations = filter_allowed_locations(all_locations)
        
        if not locations:
            # Remove temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await progress_msg.delete()
            await message.answer(
                f"❌ **Нет доступных локаций для добавления предметов**\n\n"
                f"Все локации заблокированы для бота. Обратитесь к администратору для настройки разрешенных локаций.\n\n"
                f"💡 **Подсказка:** Добавьте маркер `{config.LOCATION_MARKER}` в описание нужных локаций в HomeBox."
            )
            await state.clear()
            return
        
        # Update progress - AI analysis
        progress_msg = await update_progress_message(message, progress_msg, 'analyzing', bot_lang, 4)
        
        # Analyze image
        model = user_settings.get('model', config.DEFAULT_MODEL)
        gen_lang = user_settings.get('gen_lang', 'ru')
        
        # Extract caption (photo description) if available
        caption = message.caption if message.caption else None
        
        analysis = await analyze_image(file_path, locations, gen_lang, model, caption)
        
        # Find suggested location ID
        suggested_location_id = None
        for loc in locations:
            if loc['name'] == analysis['suggested_location']:
                suggested_location_id = str(loc['id'])
                break
        
        if not suggested_location_id:
            suggested_location_id = str(locations[0]['id'])
            analysis['suggested_location'] = locations[0]['name']
        
        # Save data
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
        
        # Form message with caption information
        caption_info = ""
        if caption and caption.strip():
            caption_info = t(bot_lang, 'caption.used') + "\n\n"
        else:
            caption_info = t(bot_lang, 'caption.not_used') + "\n\n"
        
        # Remove progress message
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        # Send result with improved formatting
        result_caption = (
            f"**{t(bot_lang, 'result.title')}**\n\n"
            f"{caption_info}"
            f"📝 **{t(bot_lang, 'field.name', value='')}**\n"
            f"`{analysis['name']}`\n\n"
            f"📋 **{t(bot_lang, 'field.description', value='')}**\n"
            f"`{analysis['description']}`\n\n"
            f"📦 **{t(bot_lang, 'field.location', value='')}**\n"
            f"`{analysis['suggested_location']}`\n\n"
            f"✨ {t(bot_lang, 'edit.what_change')}"
        )
        
        await message.answer_photo(
            photo=photo.file_id,
            caption=result_caption,
            reply_markup=create_confirmation_keyboard(locations, analysis['suggested_location'], bot_lang),
            parse_mode="Markdown"
        )
        
        await state.set_state(ItemStates.confirming_data)
        log_user_action("photo_analyzed", message.from_user.id, {
            "analysis_result": analysis,
            "model_used": model
        })
        
    except Exception as e:
        log_error(e, "photo handling", message.from_user.id)
        
        # Clean up temporary files on error
        temp_files = [f for f in os.listdir('.') if f.startswith(f'temp_{message.from_user.id}_')]
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception:
                pass
        
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
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
    bot_lang = user_settings.get('bot_lang', 'ru')
    await callback.message.answer(t(bot_lang, 'edit.enter_name'))
    await state.set_state(ItemStates.editing_name)
    await callback.answer()

@router.message(ItemStates.editing_name)
async def save_new_name(message: Message, state: FSMContext):
    """Save new item name"""
    user_data = items_data.get(message.from_user.id)
    if user_data:
        user_data['name'] = message.text
        
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        
        updated_message = (
            f"**{t(bot_lang, 'changed.name')}**\n\n"
            f"📝 **Название:** `{user_data['name']}`\n"
            f"📋 **Описание:** `{user_data['description']}`\n"
            f"📦 **Ящик:** `{user_data['location_name']}`\n\n"
            f"✨ Что еще хотите изменить?"
        )
        
        await message.answer(
            updated_message,
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name'],
                bot_lang
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
    bot_lang = user_settings.get('bot_lang', 'ru')
    await callback.message.answer(t(bot_lang, 'edit.enter_description'))
    await state.set_state(ItemStates.editing_description)
    await callback.answer()

@router.message(ItemStates.editing_description)
async def save_new_description(message: Message, state: FSMContext):
    """Save new item description"""
    user_data = items_data.get(message.from_user.id)
    if user_data:
        user_data['description'] = message.text
        
        user_settings = await db.get_user_settings(message.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        
        updated_message = (
            f"**{t(bot_lang, 'changed.description')}**\n\n"
            f"📝 **Название:** `{user_data['name']}`\n"
            f"📋 **Описание:** `{user_data['description']}`\n"
            f"📦 **Ящик:** `{user_data['location_name']}`\n\n"
            f"✨ Что еще хотите изменить?"
        )
        
        await message.answer(
            updated_message,
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name'],
                bot_lang
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
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.message.answer(
            t(bot_lang, 'edit.select_location'),
            reply_markup=create_locations_keyboard(user_data['locations'], bot_lang)
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
        # Find location name
        location_name = None
        for loc in user_data['locations']:
            if str(loc['id']) == str(location_id):
                location_name = loc['name']
                break
        
        user_data['location_id'] = str(location_id)
        user_data['location_name'] = location_name
        
        user_settings = await db.get_user_settings(callback.from_user.id)
        bot_lang = user_settings.get('bot_lang', 'ru')
        
        updated_message = (
            f"**{t(bot_lang, 'changed.location')}**\n\n"
            f"📝 **Название:** `{user_data['name']}`\n"
            f"📋 **Описание:** `{user_data['description']}`\n"
            f"📦 **Ящик:** `{user_data['location_name']}`\n\n"
            f"✨ Что еще хотите изменить?"
        )
        
        await callback.message.answer(
            updated_message,
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name'],
                bot_lang
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
        bot_lang = user_settings.get('bot_lang', 'ru')
        await callback.message.answer(
            f"{t(bot_lang, 'field.name', value=user_data['name'])}\n"
            f"{t(bot_lang, 'field.description', value=user_data['description'])}\n"
            f"**Ящик:** {user_data['location_name']}",
            reply_markup=create_confirmation_keyboard(
                user_data['locations'],
                user_data['location_name'],
                bot_lang
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
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    # Send loading indicator
    progress_msg = await callback.message.answer(t(bot_lang, 'progress.uploading'))
    
    user_data = items_data.get(callback.from_user.id)
    if user_data:
        # Make sure local file exists. If not, try to download again by file_id
        try:
            photo_path = user_data.get('photo_path')
            photo_file_id = user_data.get('photo_file_id')
            if (not photo_path) or (not os.path.exists(photo_path)):
                if photo_file_id:
                    file = await bot.get_file(photo_file_id)
                    # Restore path if missing
                    if not photo_path:
                        photo_path = f"temp_{callback.from_user.id}.jpg"
                        user_data['photo_path'] = photo_path
                    await bot.download_file(file.file_path, photo_path)
        except Exception as _:
            # Ignore, Homebox will save without photo, but we don't crash
            pass
        result = await homebox_api.create_item(
            name=user_data['name'],
            description=user_data['description'],
            location_id=user_data['location_id'],
            photo_path=user_data['photo_path']
        )
        
        # Remove progress indicator
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        if 'error' not in result:
            success_message = (
                f"**{t(bot_lang, 'added.success')}**\n\n"
                f"📝 **Предмет:** `{user_data['name']}`\n"
                f"📦 **Ящик:** `{user_data['location_name']}`\n\n"
                f"✨ {t(bot_lang, 'added.new_prompt')}\n"
            )
            
            if result.get('photo_upload') == 'failed':
                success_message += f"\n⚠️ {t(bot_lang, 'added.photo_failed')}"
            
            await callback.message.answer(
                success_message,
                parse_mode="Markdown"
            )
            if result.get('photo_upload') == 'failed':
                diagnostic = getattr(homebox_api, 'last_error', None)
                if diagnostic:
                    await callback.message.answer(
                        f"Подробности загрузки фото: {diagnostic}"
                    )
            
            # Remove temporary file
            if os.path.exists(user_data['photo_path']):
                os.remove(user_data['photo_path'])
            
            # Clear data
            del items_data[callback.from_user.id]
            # Update statistics
            await db.increment_items_processed()
            await state.set_state(ItemStates.waiting_for_photo)
        else:
            await callback.message.answer(t(bot_lang, 'added.fail'))
    
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
    bot_lang = user_settings.get('bot_lang', 'ru')
    await callback.message.answer(t(bot_lang, 'cancel.done'))
    await state.set_state(ItemStates.waiting_for_photo)
    await callback.answer()

@router.callback_query(F.data == "quick_stats")
async def quick_stats(callback: CallbackQuery):
    """Quick statistics for user"""
    user_settings = await db.get_user_settings(callback.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    stats = await db.get_bot_stats()
    uptime = await get_uptime()
    
    stats_text = (
        f"**{t(bot_lang, 'admin.stats.title')}**\n\n"
        f"👥 {t(bot_lang, 'admin.stats.users', count=len(stats.get('users_registered', [])))}\n"
        f"📦 {t(bot_lang, 'admin.stats.items', count=stats.get('items_processed', 0))}\n"
        f"⏱️ {t(bot_lang, 'admin.stats.uptime', uptime=uptime)}\n"
        f"🔄 {t(bot_lang, 'admin.stats.sessions', count=len(items_data))}"
    )
    
    await callback.message.answer(stats_text, parse_mode="Markdown")
    await callback.answer("📊 Статистика загружена")

@router.callback_query(F.data == "quick_restart")
async def quick_restart(callback: CallbackQuery, state: FSMContext):
    """Quick session restart"""
    user_settings = await db.get_user_settings(callback.from_user.id)
    bot_lang = user_settings.get('bot_lang', 'ru')
    
    # Clear current session
    if callback.from_user.id in items_data:
        user_data = items_data[callback.from_user.id]
        if os.path.exists(user_data.get('photo_path', '')):
            os.remove(user_data['photo_path'])
        del items_data[callback.from_user.id]
    
    await state.clear()
    await state.set_state(ItemStates.waiting_for_photo)
    
    await callback.message.answer(
        f"**Сессия перезапущена!**\n\n"
        f"📸 Отправьте новое фото для добавления предмета.",
        parse_mode="Markdown"
    )
    await callback.answer("🔄 Готов к новой работе")

async def main():
    dp.include_router(router)
    
    # Initialize HomeBox API with context manager
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
