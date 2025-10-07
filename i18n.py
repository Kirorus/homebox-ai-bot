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
            "💡 **Совет:** Можешь добавить описание к фото (например, \"старая книга\", \"красная кружка\") - это поможет мне точнее определить предмет!\n\n"
            "Отправь фото, чтобы начать!"
        ),
        'access.denied': '⛔️ Доступ запрещен. Обратитесь к администратору.',
        'settings.title': '⚙️ Настройки бота',
        'settings.bot_lang.title': '🌐 Язык интерфейса бота:',
        'settings.gen_lang.title': '🤖 Язык генерации названий и описаний:',
        'settings.choose_model': 'Выберите модель LLM:',
        'settings.lang.ru': '🇷🇺 Русский',
        'settings.lang.en': '🇬🇧 English',
        'settings.bot_lang.set.ru': 'Язык интерфейса установлен: Русский',
        'settings.bot_lang.set.en': 'Interface language set: English',
        'settings.gen_lang.set.ru': 'Язык генерации установлен: Русский',
        'settings.gen_lang.set.en': 'Generation language set: English',
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
        'caption.used': '📝 Использовано описание фото для улучшения распознавания',
        'caption.not_used': '📷 Распознавание только по изображению',
        'admin.stats.title': '📊 **Статистика бота**',
        'admin.stats.users': '👥 Пользователей: {count}',
        'admin.stats.items': '📦 Предметов обработано: {count}',
        'admin.stats.sessions': '🔄 Активных сессий: {count}',
        'admin.stats.uptime': '⏱ Время работы: {uptime}',
        'admin.cleanup.done': '🧹 Очистка завершена. Удалено {files} временных файлов.',
        'admin.cleanup.error': '❌ Ошибка при очистке: {error}',
        'admin.access.denied': '⛔️ Только администраторы могут использовать эту команду.',
        'admin.test_upload': '🧪 Тестирование методов загрузки фотографий...',
        'admin.test_upload.results': '📊 Результаты тестирования загрузки:\n\n{results}',
        'admin.check_api': '🔍 Проверка возможностей API HomeBox...',
        'admin.check_api.results': '📋 Результаты проверки API:\n\n{results}',
        'admin.quick_test': '⚡ Быстрый тест загрузки...',
        'admin.quick_test.success': '✅ Быстрый тест прошел успешно!',
        'admin.quick_test.failed': '❌ Быстрый тест не прошел: {error}',
        'progress.downloading': '⬇️ Скачиваю фото...',
        'progress.validating': '🔍 Проверяю изображение...',
        'progress.getting_locations': '📦 Получаю список ящиков...',
        'progress.analyzing': '🤖 Анализирую с помощью ИИ...',
        'progress.uploading': '⬆️ Загружаю в HomeBox...',
        'error.invalid_image': '❌ Ошибка с изображением: {error}',
        'error.try_again': 'Пожалуйста, отправьте другое фото (JPEG, PNG или WEBP, до 20MB).',
        'btn.prev': '« Назад',
        'btn.next': 'Вперед »',
        'model.selected': 'Модель установлена: {model}',
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
            "💡 **Tip:** You can add a description to the photo (e.g., \"old book\", \"red mug\") - this will help me identify the item more accurately!\n\n"
            "Send a photo to start!"
        ),
        'access.denied': '⛔️ Access denied. Contact administrator.',
        'settings.title': '⚙️ Bot settings',
        'settings.bot_lang.title': '🌐 Bot interface language:',
        'settings.gen_lang.title': '🤖 Item generation language:',
        'settings.choose_model': 'Choose LLM model:',
        'settings.lang.ru': '🇷🇺 Russian',
        'settings.lang.en': '🇬🇧 English',
        'settings.bot_lang.set.ru': 'Interface language set: Russian',
        'settings.bot_lang.set.en': 'Interface language set: English',
        'settings.gen_lang.set.ru': 'Generation language set: Russian',
        'settings.gen_lang.set.en': 'Generation language set: English',
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
        'caption.used': '📝 Used photo description to improve recognition',
        'caption.not_used': '📷 Recognition based on image only',
        'admin.stats.title': '📊 **Bot Statistics**',
        'admin.stats.users': '👥 Users: {count}',
        'admin.stats.items': '📦 Items processed: {count}',
        'admin.stats.sessions': '🔄 Active sessions: {count}',
        'admin.stats.uptime': '⏱ Uptime: {uptime}',
        'admin.cleanup.done': '🧹 Cleanup completed. Removed {files} temporary files.',
        'admin.cleanup.error': '❌ Cleanup error: {error}',
        'admin.access.denied': '⛔️ Only administrators can use this command.',
        'admin.test_upload': '🧪 Testing photo upload methods...',
        'admin.test_upload.results': '📊 Upload test results:\n\n{results}',
        'admin.check_api': '🔍 Checking HomeBox API capabilities...',
        'admin.check_api.results': '📋 API check results:\n\n{results}',
        'admin.quick_test': '⚡ Quick upload test...',
        'admin.quick_test.success': '✅ Quick test passed!',
        'admin.quick_test.failed': '❌ Quick test failed: {error}',
        'progress.downloading': '⬇️ Downloading photo...',
        'progress.validating': '🔍 Validating image...',
        'progress.getting_locations': '📦 Getting locations...',
        'progress.analyzing': '🤖 Analyzing with AI...',
        'progress.uploading': '⬆️ Uploading to HomeBox...',
        'error.invalid_image': '❌ Image error: {error}',
        'error.try_again': 'Please send another photo (JPEG, PNG or WEBP, up to 20MB).',
        'btn.prev': '« Prev',
        'btn.next': 'Next »',
        'model.selected': 'Model set: {model}',
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    locale = MESSAGES.get(lang) or MESSAGES[LANG_RU]
    template = locale.get(key) or MESSAGES[LANG_RU].get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template


