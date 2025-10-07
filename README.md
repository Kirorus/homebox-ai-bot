# HomeBox AI Bot

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
- **Multilingual Support**: Interface available in Russian and English
- **Settings Management**: Per-user language and model preferences

### 🔧 HomeBox Integration
- **Seamless Upload**: Direct integration with HomeBox API
- **Photo Attachment**: Automatically uploads photos as item attachments
- **Location Management**: Fetches and manages HomeBox storage locations
- **Error Handling**: Robust error handling and retry mechanisms

### 👥 User Management
- **Access Control**: Configurable user whitelist
- **User Statistics**: Track usage and performance
- **Session Management**: Handle multiple concurrent users
- **Settings Persistence**: Save user preferences

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
   python bot.py   # Direct execution
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
- **OPENAI_BASE_URL**: Use for custom OpenAI-compatible providers (e.g., Bothub)
- **HOMEBOX_TOKEN**: If not provided, bot will login using username/password
- **ALLOWED_USER_IDS**: If empty, bot is open to all users
- **OPENAI_MODEL**: Override default model selection

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

### Available Commands

#### User Commands
- `/start` - Start the bot and begin item addition process
- `/settings` - Configure language and AI model preferences
- `/myid` or `/id` - Get your Telegram user ID

#### Admin Commands
- `/stats` - View bot statistics and usage information
- `/cleanup` - Clean up temporary files
- `/testupload` - Test photo upload methods
- `/checkapi` - Check HomeBox API connectivity
- `/quicktest` - Quick upload functionality test

### Interface Features

#### Language Selection
- **Russian (🇷🇺)**: Full Russian interface
- **English (🇬🇧)**: Full English interface
- Per-user language preferences saved

#### AI Model Selection
- **GPT Models**: GPT-4o, GPT-4-turbo, GPT-5, etc.
- **Claude Models**: Claude Sonnet, Claude Opus
- **Gemini Models**: Gemini 2.5 Pro, Gemini 2.5 Flash
- **Other Models**: DeepSeek, Grok, and more

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

### Core Components

- **`bot.py`** - Main bot logic with Aiogram v3, FSM states, and handlers
- **`homebox_api.py`** - HomeBox API client with authentication and upload methods
- **`config.py`** - Environment configuration and model management
- **`database.py`** - JSON-based database for user settings and statistics
- **`i18n.py`** - Internationalization support (Russian/English)
- **`utils.py`** - Utility functions for image validation and file handling

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

## 🔧 Development

### Dependencies
```
aiogram==3.3.0          # Telegram Bot API
openai==1.12.0          # OpenAI API client
aiohttp==3.9.1          # HTTP client
python-dotenv==1.0.0    # Environment variables
httpx==0.27.2           # HTTP client
aiofiles==23.2.1        # Async file operations
pillow==10.2.0          # Image processing
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
python bot.py

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
- [ ] Persistent state storage (database)
- [ ] Batch photo processing
- [ ] Advanced location highlighting
- [ ] Custom recognition prompts
- [ ] Item search and management
- [ ] Export/import functionality
- [ ] Web dashboard
- [ ] API rate limiting
- [ ] Advanced error recovery

### Performance Improvements
- [ ] Connection pooling optimization
- [ ] Caching mechanisms
- [ ] Async processing improvements
- [ ] Memory usage optimization

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