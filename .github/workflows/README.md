# GitHub Actions Workflows

Этот каталог содержит автоматизированные процессы для CI/CD.

## 🚀 Workflows

### 1. docker-build.yml
Автоматическая сборка и загрузка Docker образа в Docker Hub.

**Триггеры:**
- Push в ветки: `main`, `master`, `develop`
- Создание тегов: `v*` (например, `v1.0.0`)
- Pull requests в `main`/`master`

**Действия:**
- Сборка multi-arch образа (linux/amd64, linux/arm64)
- Загрузка в Docker Hub с тегами:
  - `latest` (для основной ветки)
  - `branch-name` (для веток)
  - `v1.0.0` (для тегов)
- Сканирование безопасности с Trivy
- Кэширование слоев для ускорения сборки

## 🔧 Настройка

### 1. Docker Hub секреты

Добавьте в GitHub Secrets:
- `DOCKERHUB_USERNAME` - ваш логин Docker Hub
- `DOCKERHUB_TOKEN` - токен доступа Docker Hub

### 2. Создание Docker Hub токена

1. Войдите в Docker Hub
2. Перейдите в Account Settings → Security
3. Создайте новый Access Token
4. Скопируйте токен в GitHub Secrets

### 3. Проверка разрешений

Убедитесь, что репозиторий имеет права:
- `contents: read` - чтение кода
- `packages: write` - загрузка образов

## 📦 Использование готового образа

После успешной сборки образ будет доступен:

```bash
# Последняя версия
docker pull your-username/homebox-ai-bot:latest

# Конкретная ветка
docker pull your-username/homebox-ai-bot:develop

# Версия по тегу
docker pull your-username/homebox-ai-bot:v1.0.0
```

## 🔍 Мониторинг

### Просмотр статуса сборки

1. Перейдите в Actions вкладку GitHub репозитория
2. Выберите workflow "Build and Push Docker Image"
3. Просмотрите детали выполнения

### Логи сборки

В логах вы найдете:
- Информацию о сборке
- Размеры образов
- Результаты сканирования безопасности

### Уведомления

GitHub автоматически уведомит о:
- Успешной сборке
- Ошибках сборки
- Результатах сканирования безопасности

## 🛠️ Troubleshooting

### Ошибка авторизации Docker Hub

```
Error: Cannot perform an interactive login from a non TTY device
```

**Решение:** Проверьте правильность `DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN`

### Ошибка сборки

```
Error: failed to solve: failed to compute cache key
```

**Решение:** Проверьте корректность Dockerfile и .dockerignore

### Ошибка загрузки

```
Error: denied: requested access to the resource is denied
```

**Решение:** Убедитесь, что Docker Hub токен имеет права на запись

## 🔄 Обновление workflow

При изменении workflow:

1. Внесите изменения в файл
2. Сделайте commit и push
3. Проверьте выполнение в Actions
4. При необходимости откатите изменения

## 📊 Метрики

Отслеживайте:
- Время сборки
- Размер образа
- Количество скачиваний
- Уязвимости безопасности

## 🎯 Best Practices

1. **Тегирование:** Используйте семантическое версионирование
2. **Кэширование:** Включено автоматически для ускорения
3. **Безопасность:** Регулярно проверяйте результаты Trivy
4. **Мониторинг:** Следите за уведомлениями GitHub
