import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import AsyncOpenAI
import base64
import os

import config
from homebox_api import HomeboxAPI
from i18n import t

# Logging setup
logging.basicConfig(level=logging.INFO)
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

# In-memory items storage (use a DB in production)
items_data = {}
# In-memory user settings (use a DB in production)
user_settings = {}

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def analyze_image(image_path: str, locations: list, lang: str = 'ru', model: str | None = None) -> dict:
    """Analyze image via OpenAI Vision to extract item metadata."""
    base64_image = encode_image(image_path)
    
    locations_text = "\n".join([f"- {loc['name']}" for loc in locations])
    
    if lang == 'en':
        prompt = f"""Analyze this image and determine:
1. A short item name (max 50 chars)
2. A detailed description (max 200 chars)
3. Which location from the list best fits storing this item

Available locations:
{locations_text}

Answer STRICTLY in JSON format:
{{
    "name": "item name",
    "description": "item description",
    "suggested_location": "best matching location name"
}}"""
    else:
        prompt = f"""Проанализируй это изображение и определи:
1. Краткое название предмета (до 50 символов)
2. Подробное описание (до 200 символов)
3. Какая локация из списка лучше всего подходит для хранения этого предмета

Доступные локации:
{locations_text}

Ответь СТРОГО в формате JSON:
{{
    "name": "название предмета",
    "description": "описание предмета",
    "suggested_location": "название подходящей локации"
}}"""

    try:
        # Используем выбранную модель или дефолтную
        selected_model = model or config.DEFAULT_MODEL
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
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
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
        # Fallback to ru if user has no settings yet
        lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
        await message.answer(t(lang, 'access.denied'))
        return
    settings = user_settings.get(message.from_user.id) or { 'lang': 'ru', 'model': config.DEFAULT_MODEL }
    user_settings[message.from_user.id] = settings
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
    lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
    await message.answer(t(lang, 'cmd.myid', user_id=message.from_user.id))

@router.callback_query(F.data.in_({"lang_ru", "lang_en"}))
async def cb_set_lang(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
        await callback.answer(t(lang, 'access.denied'), show_alert=True)
        return
    lang = 'ru' if callback.data == 'lang_ru' else 'en'
    settings = user_settings.get(callback.from_user.id) or { 'lang': 'ru', 'model': config.DEFAULT_MODEL }
    settings['lang'] = lang
    user_settings[callback.from_user.id] = settings
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
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
        await callback.answer(t(lang, 'access.denied'), show_alert=True)
        return
    try:
        page = int(callback.data.replace("model_page_", ""))
    except Exception:
        page = 0
    settings = user_settings.get(callback.from_user.id) or { 'lang': 'ru', 'model': config.DEFAULT_MODEL }
    await callback.message.edit_reply_markup(reply_markup=models_keyboard(settings.get('model', config.DEFAULT_MODEL), page))
    await callback.answer()

@router.callback_query(F.data.startswith("model_"))
async def cb_set_model(callback: CallbackQuery):
    if config.ALLOWED_USER_IDS and callback.from_user.id not in config.ALLOWED_USER_IDS:
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
        await callback.answer(t(lang, 'access.denied'), show_alert=True)
        return
    model = callback.data.replace("model_", "")
    if model not in config.AVAILABLE_MODELS:
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
        await callback.answer(t(lang, 'settings.model.unavailable'), show_alert=True)
        return
    settings = user_settings.get(callback.from_user.id) or { 'lang': 'ru', 'model': config.DEFAULT_MODEL }
    settings['model'] = model
    user_settings[callback.from_user.id] = settings
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
    # Проверяем авторизацию пользователя
    if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
        lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
        await message.answer(t(lang, 'access.denied'))
        return
    await state.clear()
    # Инициализируем настройки по умолчанию
    if message.from_user.id not in user_settings:
        user_settings[message.from_user.id] = { 'lang': 'ru', 'model': config.DEFAULT_MODEL }
    lang = user_settings[message.from_user.id]['lang']
    await message.answer(t(lang, 'start.intro'))
    await state.set_state(ItemStates.waiting_for_photo)

@router.message(ItemStates.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Обработчик получения фотографии"""
    if config.ALLOWED_USER_IDS and message.from_user.id not in config.ALLOWED_USER_IDS:
        lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
        await message.answer(t(lang, 'access.denied'))
        return
    lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
    await message.answer(t(lang, 'analyze.progress'))
    
    # Получаем фото в максимальном качестве
    photo = message.photo[-1]
    
    # Скачиваем фото
    file = await bot.get_file(photo.file_id)
    file_path = f"temp_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    # Получаем локации из Homebox
    locations = await homebox_api.get_locations()
    
    if not locations:
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
    
    # Анализируем изображение
    settings = user_settings.get(message.from_user.id, {})
    lang = settings.get('lang', 'ru')
    model = settings.get('model', config.DEFAULT_MODEL)
    analysis = await analyze_image(file_path, locations, lang, model)
    
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
        'locations': locations
    }
    
    # Отправляем результат
    await message.answer_photo(
        photo=photo.file_id,
        caption=(
            t(lang, 'result.title')
            + t(lang, 'field.name', value=analysis['name']) + "\n\n"
            + t(lang, 'field.description', value=analysis['description']) + "\n\n"
            + t(lang, 'field.location', value=analysis['suggested_location']) + "\n\n"
            + t(lang, 'edit.what_change')
        ),
        reply_markup=create_confirmation_keyboard(locations, analysis['suggested_location']),
        parse_mode="Markdown"
    )
    
    await state.set_state(ItemStates.confirming_data)

@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    """Edit item name"""
    # Remove buttons from the previous message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
    await callback.message.answer(t(lang, 'edit.enter_name'))
    await state.set_state(ItemStates.editing_name)
    await callback.answer()

@router.message(ItemStates.editing_name)
async def save_new_name(message: Message, state: FSMContext):
    """Сохранение нового названия"""
    user_data = items_data.get(message.from_user.id)
    if user_data:
        user_data['name'] = message.text
        
        lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
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
    lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
    await callback.message.answer(t(lang, 'edit.enter_description'))
    await state.set_state(ItemStates.editing_description)
    await callback.answer()

@router.message(ItemStates.editing_description)
async def save_new_description(message: Message, state: FSMContext):
    """Сохранение нового описания"""
    user_data = items_data.get(message.from_user.id)
    if user_data:
        user_data['description'] = message.text
        
        lang = (user_settings.get(message.from_user.id) or {}).get('lang', 'ru')
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
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
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
        
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
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
        lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
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
    lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
    await callback.message.answer(t(lang, 'confirm.adding'))
    
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
    
    lang = (user_settings.get(callback.from_user.id) or {}).get('lang', 'ru')
    await callback.message.answer(t(lang, 'cancel.done'))
    await state.set_state(ItemStates.waiting_for_photo)
    await callback.answer()

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
