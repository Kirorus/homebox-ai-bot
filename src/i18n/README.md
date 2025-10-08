# Internationalization (i18n) System

This directory contains the internationalization system for the HomeBox AI Bot.

## Structure

```
src/i18n/
├── __init__.py              # Module initialization
├── i18n_manager.py          # Main i18n manager class
├── utils.py                 # i18n utilities and helpers
├── locales/                 # Translation files
│   ├── en.json             # English translations
│   ├── ru.json             # Russian translations
│   ├── de.json             # German translations
│   ├── fr.json             # French translations
│   └── es.json             # Spanish translations
└── README.md               # This file
```

## Usage

### Basic Translation

```python
from i18n import t

# Get translated text
text = t('en', 'settings.title')  # Returns "Settings"
text = t('ru', 'settings.title')  # Returns "Настройки"
```

### With Parameters

```python
# Translation with parameters
text = t('en', 'item.success', name="My Item")
# Returns "Item My Item created successfully!"
```

### Language Names

```python
from i18n import get_language_name

# Get language display name
name = get_language_name('de', 'en')  # Returns "Deutsch"
name = get_language_name('ru', 'ru')  # Returns "Русский"
```

## Adding New Languages

1. Create a new JSON file in `locales/` directory (e.g., `it.json` for Italian)
2. Copy the structure from an existing language file
3. Translate all the values
4. Add the language code to `supported_languages` in `i18n_manager.py`
5. Update keyboard handlers to include the new language

## Translation Keys Structure

The translation keys are organized hierarchically:

- `common.*` - Common UI elements (buttons, navigation)
- `start.*` - Welcome and start messages
- `settings.*` - Settings interface
- `languages.*` - Language names
- `item.*` - Item-related messages
- `edit.*` - Editing interface
- `buttons.*` - Button labels
- `errors.*` - Error messages
- `processing.*` - Processing messages
- `success.*` - Success messages
- `stats.*` - Statistics interface
- `restart.*` - Restart messages

## Best Practices

1. **Consistency**: Use consistent terminology across all languages
2. **Context**: Provide context in translation keys (e.g., `settings.bot_lang` vs `settings.gen_lang`)
3. **Fallbacks**: The system automatically falls back to English if a translation is missing
4. **Parameters**: Use named parameters for dynamic content
5. **Testing**: Test all languages to ensure UI elements fit properly

## Example Translation File

```json
{
  "common": {
    "back": "⬅️ Back",
    "cancel": "❌ Cancel",
    "confirm": "✅ Confirm"
  },
  "settings": {
    "title": "Settings",
    "bot_lang": "Bot Language"
  }
}
```

## Error Handling

- If a translation key is not found, the key itself is returned
- If a language is not supported, it falls back to English
- All errors are logged for debugging
