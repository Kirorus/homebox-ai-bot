#!/bin/bash

# Скрипт для остановки бота HomeBox AI

echo "🛑 Остановка HomeBox AI Bot..."

# Находим и останавливаем все экземпляры бота
BOT_PIDS=$(ps aux | grep "python bot.py" | grep -v grep | awk '{print $2}')

if [ -z "$BOT_PIDS" ]; then
    echo "ℹ️  Бот не запущен"
    exit 0
fi

echo "🔍 Найдены экземпляры бота: $BOT_PIDS"

for PID in $BOT_PIDS; do
    echo "🛑 Останавливаем процесс $PID..."
    kill $PID
    sleep 2
    
    # Проверяем, что процесс действительно остановлен
    if ps -p $PID > /dev/null 2>&1; then
        echo "🔨 Принудительно завершаем процесс $PID..."
        kill -9 $PID
    fi
done

echo "✅ Все экземпляры бота остановлены"
