from typing import Dict


LANG_RU = 'ru'
LANG_EN = 'en'


MESSAGES: Dict[str, Dict[str, str]] = {
    LANG_RU: {
        'start.intro': (
            "👋 Привет! Я помогу добавить предметы в твой Homebox.\n\n"
            "📸 Просто отправь мне фотографию предмета, и я:\n"
            "• Определю что это\n"
            "• Создам название и описание\n"
            "• Предложу подходящий ящик\n"
            "• Позволю всё отредактировать\n"
            "• Добавлю в Homebox\n\n"
            "Отправь фото, чтобы начать!"
        ),
        'access.denied': '⛔️ Доступ запрещен. Обратитесь к администратору.',
        'settings.title': '⚙️ Настройки бота\n\nВыберите язык распознавания:',
        'settings.choose_model': 'Выберите модель LLM:',
        'settings.lang.ru': '🇷🇺 Русский',
        'settings.lang.en': '🇬🇧 English',
        'settings.lang.set.ru': 'Язык распознавания установлен: Русский',
        'settings.lang.set.en': 'Recognition language set: English',
        'settings.model.unavailable': 'Модель недоступна',
        'analyze.progress': '🔍 Анализирую изображение...',
        'homebox.locations.fail': '❌ Не удалось получить список ящиков из Homebox',
        'cmd.myid': 'Ваш Telegram ID: {user_id}',
        'result.title': '📋 **Результат распознавания:**\n\n',
        'field.name': '**Название:** {value}',
        'field.description': '**Описание:** {value}',
        'field.location': '**Предложенный ящик:** {value}',
        'edit.what_change': 'Что хочешь изменить?',
        'btn.edit.name': '✏️ Изменить название',
        'btn.edit.description': '📝 Изменить описание',
        'btn.edit.location': '📦 Изменить ящик',
        'btn.confirm': '✅ Подтвердить и добавить',
        'btn.cancel': '❌ Отменить',
        'edit.enter_name': '✏️ Введи новое название:',
        'edit.enter_description': '📝 Введи новое описание:',
        'edit.select_location': '📦 Выбери ящик:',
        'changed.name': '✅ Название изменено!',
        'changed.description': '✅ Описание изменено!',
        'changed.location': '✅ Ящик изменен!',
        'back': '« Назад',
        'confirm.adding': '⏳ Добавляю предмет в Homebox...',
        'added.success': '✅ **Предмет успешно добавлен!**',
        'added.new_prompt': 'Отправь новое фото, чтобы добавить еще один предмет.',
        'added.photo_failed': '⚠️ Не удалось загрузить фото.',
        'added.fail': '❌ Ошибка при добавлении предмета в Homebox. Попробуй еще раз.',
        'cancel.done': '❌ Операция отменена. Отправь новое фото, чтобы начать заново.',
    },
    LANG_EN: {
        'start.intro': (
            "👋 Hi! I can help add items to your Homebox.\n\n"
            "📸 Just send me a photo and I will:\n"
            "• Recognize the item\n"
            "• Propose a name and description\n"
            "• Suggest the best box\n"
            "• Let you edit details\n"
            "• Add it to Homebox\n\n"
            "Send a photo to start!"
        ),
        'access.denied': '⛔️ Access denied. Contact administrator.',
        'settings.title': '⚙️ Bot settings\n\nChoose recognition language:',
        'settings.choose_model': 'Choose LLM model:',
        'settings.lang.ru': '🇷🇺 Russian',
        'settings.lang.en': '🇬🇧 English',
        'settings.lang.set.ru': 'Recognition language set: Russian',
        'settings.lang.set.en': 'Recognition language set: English',
        'settings.model.unavailable': 'Model is not available',
        'analyze.progress': '🔍 Analyzing image...',
        'homebox.locations.fail': '❌ Failed to fetch Homebox locations',
        'cmd.myid': 'Your Telegram ID: {user_id}',
        'result.title': '📋 **Recognition result:**\n\n',
        'field.name': '**Name:** {value}',
        'field.description': '**Description:** {value}',
        'field.location': '**Suggested box:** {value}',
        'edit.what_change': 'What would you like to change?',
        'btn.edit.name': '✏️ Edit name',
        'btn.edit.description': '📝 Edit description',
        'btn.edit.location': '📦 Change box',
        'btn.confirm': '✅ Confirm and add',
        'btn.cancel': '❌ Cancel',
        'edit.enter_name': '✏️ Enter a new name:',
        'edit.enter_description': '📝 Enter a new description:',
        'edit.select_location': '📦 Choose a box:',
        'changed.name': '✅ Name updated!',
        'changed.description': '✅ Description updated!',
        'changed.location': '✅ Box updated!',
        'back': '« Back',
        'confirm.adding': '⏳ Adding item to Homebox...',
        'added.success': '✅ **Item added successfully!**',
        'added.new_prompt': 'Send a new photo to add another item.',
        'added.photo_failed': '⚠️ Failed to upload photo.',
        'added.fail': '❌ Failed to add item to Homebox. Try again.',
        'cancel.done': '❌ Operation canceled. Send a new photo to restart.',
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    locale = MESSAGES.get(lang) or MESSAGES[LANG_RU]
    template = locale.get(key) or MESSAGES[LANG_RU].get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template


