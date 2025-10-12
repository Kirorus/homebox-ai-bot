# Исправление проблем с правами доступа Docker

## Проблема
```
PermissionError: [Errno 13] Permission denied: '/app/logs/bot.log'
```

## Решение

### Вариант 1: Автоматическое исправление (рекомендуется)
```bash
sudo ./fix-docker-permissions.sh
```

### Вариант 2: Ручное исправление
```bash
# 1. Остановить контейнеры
sudo docker compose down

# 2. Исправить права на папки
sudo chown -R $(id -u):$(id -g) logs data temp
sudo chmod -R 755 logs data temp
sudo chmod 644 logs/bot.log 2>/dev/null || true

# 3. Пересобрать образ (важно: с --no-cache)
sudo docker build --no-cache -t kirorus/homebox-ai-bot:latest .

# 4. Запустить контейнеры
sudo docker compose up -d
```

### Вариант 3: Добавить пользователя в группу docker (постоянное решение)
```bash
sudo usermod -aG docker $USER
# После этого нужно перелогиниться или выполнить:
newgrp docker
```

## Проверка
```bash
# Проверить логи
sudo docker compose logs -f

# Проверить статус контейнеров
sudo docker compose ps
```

## Что было исправлено
1. В `Dockerfile` изменен пользователь `bot` на UID/GID 1000 (соответствует пользователю kiroru)
2. Создан скрипт автоматического исправления прав доступа
3. Исправлены права на хост-директории
