# HomeBox AI Bot
[![codecov](https://codecov.io/gh/Kirorus/homebox-ai-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/Kirorus/homebox-ai-bot)

An intelligent Telegram bot that uses AI vision to automatically add items to your HomeBox inventory. Simply send a photo of an item, and the bot will recognize it, suggest a name and description, recommend the best storage location, and add it to your HomeBox with the photo attached.

## ✨ Features

### 🤖 AI-Powered Recognition
- **Photo Analysis**: Uses OpenAI Vision (or compatible APIs) to analyze item photos
- **Smart Suggestions**: Automatically generates item names, descriptions, and optimal storage locations
- **Caption Support**: Can use photo captions to improve recognition accuracy
- **Multiple Models**: Support for various LLM models (GPT-4, Claude, Gemini, etc.)

### 🎛️ User-Friendly Interface
- **Interactive Editing**: Edit name, description, and location before adding to HomeBox
- **Progress Tracking**: Real-time progress updates during processing
- **Multilingual Support**: Interface available in 5 languages (English, Russian, German, French, Spanish)
- **Settings Management**: Per-user language and model preferences
- **i18n System**: Professional internationalization with easy language addition

### 🔧 HomeBox Integration
- **Seamless Upload**: Direct integration with HomeBox API
- **Photo Attachment**: Automatically uploads photos as item attachments
- **Location Management**: Fetches and manages HomeBox storage locations
- **Item Search**: Search through your HomeBox inventory with text queries
- **Image Display**: View item photos directly in search results and item details
- **Error Handling**: Robust error handling and retry mechanisms

### 👥 User Management
- **Access Control**: Configurable user whitelist
- **User Statistics**: Track usage and performance
- **Session Management**: Handle multiple concurrent users
- **Settings Persistence**: Save user preferences

### 🛡️ Enhanced Features

#### Error Handling & Logging
- **Comprehensive Logging**: Detailed error tracking with context and user information
- **JSON Error Logs**: Structured error logging in `errors.log` for better analysis
- **User Action Tracking**: Analytics and debugging support with detailed logging
- **Graceful Recovery**: Robust error handling with automatic retry mechanisms
- **Debug Mode**: Enhanced DEBUG-level logging for development and troubleshooting

#### Performance & Reliability
- **Uptime Tracking**: Monitor bot availability and performance with detailed uptime reporting
- **Statistics Dashboard**: Real-time usage analytics via `/stats` command
- **Temporary File Management**: Automatic cleanup of processing files and temp directories
- **Memory Management**: Efficient handling of image processing and API calls
- **Process Management**: Safe startup/shutdown scripts prevent conflicts and duplicate instances

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token
- OpenAI API access (or compatible provider)
- HomeBox server access

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd homebox-ai-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp sample.env .env
   # Edit .env with your configuration
   ```

5. **Run the bot**
   ```bash
   ./start_bot.sh  # Linux/Mac
   # or
   python src/main.py   # Direct execution
   ```

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
HOMEBOX_URL=http://your-homebox-url:7745

# Optional
OPENAI_BASE_URL=https://bothub.chat/api/v2/openai/v1  # Custom OpenAI endpoint
HOMEBOX_TOKEN=your_homebox_token                      # Or use username/password
HOMEBOX_USER=your_homebox_username
HOMEBOX_PASSWORD=your_homebox_password
ALLOWED_USER_IDS=123456789,987654321                  # Comma-separated user IDs
OPENAI_MODEL=gpt-4o                                   # Default model
```

### Configuration Notes
- **OPENAI_BASE_URL**: Use for custom OpenAI-compatible providers (e.g., Bothub, Ollama)
- **HOMEBOX_TOKEN**: If not provided, bot will login using username/password
- **ALLOWED_USER_IDS**: If empty, bot is open to all users (comma-separated list)
- **OPENAI_MODEL**: Override default model selection (defaults to gpt-4o)
- **Model Support**: Supports 20+ models including GPT, Claude, Gemini, DeepSeek, and Grok

## 📱 Usage

### Basic Workflow

1. **Start the bot**: Send `/start` to begin
2. **Send a photo**: Upload an image of the item you want to add
3. **Review suggestions**: The bot will analyze and suggest:
   - Item name
   - Description
   - Best storage location
4. **Edit if needed**: Use buttons to modify any suggestions
5. **Confirm**: Add the item to HomeBox with photo attached

### 🔍 Search & Browse Features

#### Item Search
- **Text Search**: Search items by name or description using `/search` command
- **Recent Items**: View recently added items with `/recent` command
- **Image Gallery**: Items with photos are displayed as image galleries
- **Pagination**: Navigate through search results with page controls
- **Item Details**: Click on any item to view full details with photos

#### Search Interface
- **Smart Results**: Search results show item name, location, and description
- **Photo Preview**: Items with images display thumbnails in search results
- **Quick Actions**: Easy navigation between search results and item details
- **Fallback Support**: Graceful handling when images are unavailable

#### Image Display
- **High-Quality Photos**: Full-resolution images in item details
- **Media Groups**: Multiple items displayed as photo galleries
- **Caption Support**: Item information displayed with each photo
- **Error Handling**: Automatic fallback to text when images fail to load

### 📦 Advanced Item Management

#### Item Card Actions
- **Move Items**: Relocate items between different storage locations
- **Edit Names**: Update item names directly from the item card
- **Edit Descriptions**: Modify item descriptions inline
- **Reanalyze Items**: Re-run AI analysis with user hints for better recognition
- **Location Filtering**: Only show relevant locations based on configured markers

#### Item Movement
- **Smart Location Selection**: Filter available locations based on markers
- **One-Click Moving**: Simple interface for relocating items
- **Progress Feedback**: Real-time updates during item movement
- **Error Handling**: Graceful handling of movement failures

#### Item Reanalysis
- **AI-Powered Reanalysis**: Use AI vision to re-analyze existing items
- **User Hints**: Provide additional context to improve recognition
- **Image Processing**: Download and analyze item photos from HomeBox
- **Automatic Updates**: Update item details based on new analysis
- **Temporary File Management**: Automatic cleanup of downloaded images

### 🏷️ Location Management System

#### Location Marking
- **TGB Tags**: Mark locations with `[TGB]` tags for easy identification
- **Visual Selection**: Interactive interface to select/deselect locations
- **Batch Operations**: Apply markers to multiple locations at once
- **Status Tracking**: Visual indicators (✅/⬜) for marked/unmarked locations
- **Pagination**: Navigate through large location lists

#### Location Viewing
- **Complete Overview**: View all locations with their marker status
- **Summary Statistics**: Count of marked vs unmarked locations
- **Pagination**: Handle large location lists with page navigation
- **Quick Navigation**: Easy switching between location management functions

#### Location Configuration
- **Filter Modes**: Configure which locations are available for item creation
- **Marker-Based Filtering**: Use `[TGB]` markers to filter available locations
- **Settings Integration**: Location management accessible through settings menu
- **Persistent Configuration**: Settings saved per user

#### AI-Powered Location Descriptions
- **Smart Description Generation**: Use AI to automatically generate location descriptions based on stored items
- **Item-Based Analysis**: AI analyzes items in each location to create meaningful descriptions
- **User Model Selection**: Uses the same AI model as configured for photo analysis
- **Interactive Confirmation**: Review and edit generated descriptions before applying
- **Parent Location Preservation**: Maintains location hierarchy when updating descriptions
- **Batch Processing**: Generate descriptions for multiple locations efficiently

### Available Commands

#### User Commands
- `/start` - Start the bot and begin item addition process
- `/settings` - Configure language, AI model preferences, and location management
- `/myid` or `/id` - Get your Telegram user ID
- `/search` - Search for items in your HomeBox inventory
- `/recent` - View recent items from your HomeBox

#### Item Management Features
- **Move Items**: Relocate items between storage locations from item details
- **Edit Item Names**: Update item names directly from item cards
- **Edit Descriptions**: Modify item descriptions inline
- **Reanalyze Items**: Re-run AI analysis with user hints for better recognition
- **Location Management**: Mark/unmark locations with `[TGB]` tags
- **View All Locations**: Browse all locations with marker status

#### Admin Commands
- `/stats` - View bot statistics and usage information
- `/cleanup` - Clean up temporary files
- `/testupload` - Test photo upload methods
- `/checkapi` - Check HomeBox API connectivity
- `/quicktest` - Quick upload functionality test
- `/test_items` - Test HomeBox items API
- `/test_search` - Test search functionality

### Interface Features

#### Language Selection
- **Russian (🇷🇺)**: Full Russian interface
- **English (🇬🇧)**: Full English interface
- Per-user language preferences saved

#### AI Model Selection
- **GPT Models**: GPT-4o, GPT-4-turbo, GPT-5, GPT-4.1, GPT-5-nano, GPT-5-chat, GPT-5-pro, etc.
- **Claude Models**: Claude Sonnet 4, Claude Sonnet 4.5, Claude Opus 4
- **Gemini Models**: Gemini 2.5 Pro, Gemini 2.5 Flash
- **DeepSeek Models**: DeepSeek Chat v3, DeepSeek R1, DeepSeek v3.2, DeepSeek v3.1
- **Other Models**: Grok-4, Gemma-3-4b-it, and more

#### Photo Processing
- **Supported Formats**: JPEG, PNG, WEBP
- **Size Limit**: Up to 20MB
- **Caption Support**: Add descriptions to improve recognition
- **Progress Updates**: Real-time processing status

## 🛠️ Management

### Bot Control Scripts

#### Start Bot
```bash
./start_bot.sh
```
- Automatically stops any running instances
- Prevents conflicts and duplicate processes
- Safe startup with error handling

#### Stop Bot
```bash
./stop_bot.sh
```
- Gracefully stops all bot instances
- Force-kills if necessary
- Complete cleanup

### Manual Management
```bash
# Check running instances
ps aux | grep "python bot.py"

# Stop all instances
pkill -f "python bot.py"

# View logs
tail -f bot.log
```

### Systemd Service (Optional)
For automatic startup on system boot:

```bash
# Create service file
sudo nano /etc/systemd/system/homebox-bot.service

# Add configuration:
[Unit]
Description=HomeBox AI Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/homebox-ai-bot
ExecStart=/path/to/homebox-ai-bot/start_bot.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable homebox-bot.service
sudo systemctl start homebox-bot.service
```

## 🏗️ Architecture

### New Modular Architecture (v2.0)

The bot has been refactored into a clean, modular architecture with clear separation of concerns:

```
src/
├── bot/                    # Bot-specific code
│   ├── handlers/          # Message and callback handlers
│   ├── keyboards/         # Inline keyboard management
│   └── states.py          # FSM states
├── config/                # Configuration management
├── models/                # Data models with validation
├── services/              # Business logic services
├── utils/                 # Utility functions
└── main.py               # Application entry point
```

### Core Components

- **`src/main.py`** - Application entry point with dependency injection
- **`src/bot/handlers/`** - Modular message handlers (photo, settings, admin)
- **`src/services/`** - Business logic services (AI, HomeBox, Image, Database)
- **`src/models/`** - Type-safe data models with validation
- **`src/config/`** - Centralized configuration with validation
- **`src/utils/`** - Reusable utility functions
- **`start_bot.sh`** - Safe startup script with automatic instance management
- **`stop_bot.sh`** - Graceful shutdown script for all bot instances

### FSM States
- `waiting_for_photo` - Waiting for user to send photo
- `confirming_data` - Showing recognition results for confirmation
- `editing_name` - User editing item name
- `editing_description` - User editing item description
- `selecting_location` - User selecting storage location

### Data Flow
1. User sends photo → Download and validate
2. Fetch HomeBox locations → AI analysis
3. Present results → User review/edit
4. Create HomeBox item → Upload photo
5. Confirm success → Clean up temp files

### 🆕 New Features in v2.1

#### Advanced Item Management
The bot now provides comprehensive item management capabilities directly from item cards:

**Item Movement**
- Move items between different storage locations
- Smart location filtering based on configured markers
- Real-time progress feedback during movement
- Error handling for failed movements

**Item Editing**
- Edit item names directly from item details
- Modify item descriptions inline
- Changes are immediately saved to HomeBox
- User-friendly editing interface

**AI Reanalysis**
- Re-run AI analysis on existing items with user hints
- Download and analyze item photos from HomeBox
- Provide additional context to improve recognition
- Automatic cleanup of temporary files

#### Location Management System
Complete location management system with visual markers:

**TGB Tag System**
- Mark locations with `[TGB]` tags for easy identification
- Visual selection interface with ✅/⬜ indicators
- Batch operations for multiple locations
- Pagination for large location lists

**Location Viewing**
- View all locations with their marker status
- Summary statistics (marked vs unmarked)
- Page navigation for large lists
- Quick switching between management functions

**AI-Powered Location Descriptions**
- **Smart Description Generation**: Automatically generate meaningful descriptions for locations based on stored items
- **Item Analysis**: AI analyzes items in each location to understand their purpose and create relevant descriptions
- **Model Consistency**: Uses the same AI model as configured for photo analysis in user settings
- **Interactive Workflow**: Review generated descriptions with Yes/No/Regenerate options before applying
- **Hierarchy Preservation**: Maintains parent-child location relationships when updating descriptions
- **Batch Processing**: Generate descriptions for multiple locations efficiently
- **Error Handling**: Robust error handling with fallback mechanisms for API failures

**Settings Integration**
- Location management accessible through settings menu
- Persistent configuration per user
- Seamless integration with existing settings

#### Technical Improvements
- Fixed callback data length issues (64-byte limit)
- Proper FSM state management
- Enhanced error handling and logging
- Optimized API calls and data flow
- Improved user experience with pagination
- Fixed parent location preservation in API updates
- Enhanced Location model parsing for nested parent objects

### 🌍 Internationalization (i18n)

The bot includes a professional internationalization system:

- **5 Languages**: English, Russian, German, French, Spanish
- **Easy Extension**: Add new languages by creating JSON translation files
- **Fallback System**: Automatic fallback to English for missing translations
- **Parameter Support**: Dynamic content with named parameters
- **Consistent Structure**: Hierarchical translation keys for easy management

#### Adding a New Language

1. Create `src/i18n/locales/[lang].json` (e.g., `it.json` for Italian)
2. Copy structure from existing language file
3. Translate all values
4. Add language code to `supported_languages` in `i18n_manager.py`
5. Update keyboard handlers to include new language

#### Translation Usage

```python
from i18n import t

# Basic translation
text = t('en', 'settings.title')  # "Settings"
text = t('ru', 'settings.title')  # "Настройки"

# With parameters
text = t('en', 'item.success', name="My Item")
# "Item My Item created successfully!"
```

## 🔧 Development

### Dependencies
```
aiogram==3.22.0         # Telegram Bot API
openai==2.2.0           # OpenAI API client
python-dotenv==1.1.1    # Environment variables
aiohttp==3.12.15        # HTTP client
pillow==11.3.0          # Image processing
aiofiles==24.1.0        # Async file operations
aiosqlite==0.21.0       # SQLite database
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
python src/main.py

# Check logs
tail -f bot.log
```

### Testing
- Use `/testupload` to test photo upload functionality
- Use `/checkapi` to verify HomeBox connectivity
- Use `/quicktest` for quick functionality verification

## 📊 Monitoring

### Logs
- **`bot.log`** - Detailed application logs
- **`errors.log`** - Error-specific logs
- Real-time logging with configurable levels

### Statistics
- User count and activity
- Items processed
- Active sessions
- Uptime tracking
- API usage statistics

### Health Checks
- HomeBox API connectivity
- OpenAI API status
- File system health
- Memory usage monitoring

## 🚨 Troubleshooting

### Common Issues

#### Bot Not Responding
- Check for multiple running instances: `ps aux | grep "python bot.py"`
- Stop all instances: `./stop_bot.sh`
- Restart: `./start_bot.sh`

#### API Errors
- Verify environment variables in `.env`
- Check HomeBox server accessibility
- Validate OpenAI API key and limits
- Use `/checkapi` for diagnostics

#### Photo Upload Issues
- Ensure photo format is supported (JPEG, PNG, WEBP)
- Check file size (max 20MB)
- Verify HomeBox API permissions
- Use `/testupload` for testing

#### Recognition Problems
- Try different AI models via `/settings`
- Add photo captions for better context
- Check OpenAI API quota and limits
- Verify model availability

### Debug Commands
- `/stats` - View bot statistics
- `/checkapi` - Test API connectivity
- `/testupload` - Test upload methods
- `/cleanup` - Clean temporary files

## 🔮 Roadmap

### Planned Features
- [x] **COMPLETED**: Advanced item management (move, edit, reanalyze)
- [x] **COMPLETED**: Location management system with TGB tags
- [x] **COMPLETED**: Item reanalysis with AI and user hints
- [x] **COMPLETED**: Smart location filtering based on markers
- [x] **COMPLETED**: Comprehensive location viewing and management
- [x] **COMPLETED**: Enhanced settings interface with location management
- [x] **COMPLETED**: AI-powered location description generation
- [x] **COMPLETED**: Interactive description confirmation workflow
- [x] **COMPLETED**: Parent location preservation during updates
- [ ] Complete admin handlers
- [ ] Batch photo processing (multiple items at once)
- [ ] Advanced location highlighting with visual maps
- [ ] Custom recognition prompts and templates
- [ ] Export/import functionality (CSV, JSON)
- [ ] Web dashboard for administration
- [ ] API rate limiting and usage quotas
- [ ] Advanced error recovery and auto-restart
- [ ] Photo quality enhancement and preprocessing
- [ ] Integration with additional storage providers
- [ ] Real-time notifications and webhooks
- [ ] Advanced search filters (by location, date, tags)
- [ ] Bulk operations on search results

### Performance Improvements
- [x] Enhanced logging and error tracking
- [x] Process management and conflict prevention
- [x] Temporary file cleanup automation
- [x] Modular architecture with clean separation
- [x] Type-safe models with validation
- [x] Service-based architecture
- [x] Image URL optimization with proper API endpoints
- [x] Media group handling for efficient image display
- [x] Fallback mechanisms for failed image loads
- [ ] Connection pooling optimization
- [ ] Caching mechanisms for API responses
- [ ] Async processing improvements
- [ ] Memory usage optimization
- [ ] Image compression and optimization

### Current Status (v2.1)
- ✅ Core functionality fully implemented
- ✅ Multi-language support (5 languages: EN, RU, DE, FR, ES)
- ✅ 20+ AI model support
- ✅ Robust error handling and logging
- ✅ Safe process management
- ✅ User access control
- ✅ Statistics and monitoring
- ✅ HomeBox API integration
- ✅ Modular architecture with clean separation
- ✅ Type-safe models with validation
- ✅ Service-based architecture
- ✅ SQLite database integration
- ✅ Item search functionality with text queries
- ✅ Image display in search results and item details
- ✅ Pagination and navigation controls
- ✅ Media group support for multiple images
- ✅ Fallback handling for missing images
- ✅ **NEW**: Advanced item management (move, edit, reanalyze)
- ✅ **NEW**: Location management system with TGB tags
- ✅ **NEW**: Item reanalysis with AI and user hints
- ✅ **NEW**: Smart location filtering based on markers
- ✅ **NEW**: Comprehensive location viewing and management
- ✅ **NEW**: Batch location marking operations
- ✅ **NEW**: Enhanced settings interface with location management
- ✅ **NEW**: AI-powered location description generation
- ✅ **NEW**: Interactive description confirmation workflow
- ✅ **NEW**: Parent location preservation during updates
- ✅ **NEW**: Model consistency between photo analysis and description generation

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review logs for error details
- Open an issue on GitHub
- Contact the administrator

---

**HomeBox AI Bot** - Making inventory management intelligent and effortless! 🤖📦