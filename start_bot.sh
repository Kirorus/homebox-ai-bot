#!/bin/bash

# Скрипт для безопасного запуска бота HomeBox AI
# Автоматически останавливает предыдущие экземпляры

echo "🤖 Запуск HomeBox AI Bot..."

# Переходим в директорию проекта
cd "$(dirname "$0")"

# Проверяем, запущен ли уже бот
BOT_PID=$(ps aux | grep "python bot.py" | grep -v grep | awk '{print $2}')

if [ ! -z "$BOT_PID" ]; then
    echo "⚠️  Найден запущенный экземпляр бота (PID: $BOT_PID)"
    echo "🛑 Останавливаем предыдущий экземпляр..."
    kill $BOT_PID
    sleep 2
    
    # Проверяем, что процесс действительно остановлен
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "🔨 Принудительно завершаем процесс..."
        kill -9 $BOT_PID
        sleep 1
    fi
    
    echo "✅ Предыдущий экземпляр остановлен"
fi

# Активируем виртуальное окружение и запускаем бота
echo "🚀 Запускаем новый экземпляр бота..."
source venv/bin/activate
python bot.py
