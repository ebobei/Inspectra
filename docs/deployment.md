# Deployment Guide

Краткая инструкция по запуску Inspectra в self-hosted окружении.

## Требования

Для локального или внутреннего запуска нужны:

- Docker;
- Docker Compose;
- доступ к Jira;
- доступ к LLM API или локальному LLM-compatible endpoint.

## Состав сервисов

Inspectra запускается через Docker Compose и состоит из нескольких сервисов:

```text
ui        - frontend и nginx proxy
api       - backend API
worker    - фоновая обработка review-задач
postgres  - база данных
redis     - очередь задач
```

Наружу публикуется только UI/nginx.

API доступен через proxy по пути:

```text
/api
```

## Подготовка `.env`

Создайте `.env` из примера:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Минимально нужно настроить Jira и LLM.

## Настройка Jira

```env
JIRA_BASE_URL=https://jira.example.com
JIRA_USERNAME=user@example.com
JIRA_API_TOKEN=your-token
```

Пользователь Jira должен иметь права:

- читать задачи;
- читать комментарии;
- создавать комментарии;
- обновлять комментарии, созданные этим пользователем.

## Настройка LLM

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
LLM_VERIFY_SSL=true
```

Для локального LLM gateway укажите его URL:

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=local
LLM_MODEL=qwen2.5:7b
```

Конкретные значения зависят от используемого LLM-compatible API.

## SSL в корпоративной сети

В корпоративных сетях HTTPS-запросы могут ломаться из-за внутренних сертификатов.

Для диагностики можно временно отключить проверку SSL при обращении к LLM API:

```env
LLM_VERIFY_SSL=false
```

Это снижает безопасность и не должно использоваться без необходимости.

## Настройка внешнего порта

По умолчанию используется порт:

```env
UI_PORT=18080
```

UI будет доступен по адресу:

```text
http://localhost:18080
```

Если порт занят, измените его:

```env
UI_PORT=19080
```

После изменения перезапустите проект:

```bash
docker compose down
docker compose up --build
```

## Запуск

```bash
docker compose up --build
```

Проверка:

```text
http://localhost:18080/api/health
```

Документация API:

```text
http://localhost:18080/api/docs
```

## Остановка

```bash
docker compose down
```

## Полная очистка локальных данных

```bash
docker compose down -v
```

Эта команда удаляет Docker volumes, включая данные PostgreSQL.

## Обновление после изменений кода

```bash
docker compose down
docker compose up --build
```

## Проверка конфигурации Compose

```bash
docker compose config
```

## Проверка логов

Все сервисы:

```bash
docker compose logs
```

Конкретный сервис:

```bash
docker compose logs api
docker compose logs worker
docker compose logs ui
```

Логи в режиме follow:

```bash
docker compose logs -f
```

## Базовая диагностика

### UI не открывается

Проверьте, что порт не занят:

```bash
docker compose ps
```

И проверьте значение:

```env
UI_PORT=18080
```

### API недоступен

Проверьте health endpoint:

```text
http://localhost:18080/api/health
```

Проверьте логи backend:

```bash
docker compose logs api
```

### Worker не обрабатывает задачи

Проверьте логи worker:

```bash
docker compose logs worker
```

Проверьте Redis URL:

```env
REDIS_URL=redis://redis:6379/0
```

### Ошибки Jira

Проверьте:

- `JIRA_BASE_URL`;
- логин;
- токен;
- права пользователя на чтение задач и публикацию комментариев.

### Ошибки LLM

Проверьте:

- `LLM_BASE_URL`;
- `LLM_API_KEY`;
- `LLM_MODEL`;
- доступность LLM API из контейнера;
- настройку `LLM_VERIFY_SSL`.

## Production-подход

Для внутреннего production-like запуска рекомендуется:

- не публиковать PostgreSQL и Redis наружу;
- использовать отдельные секреты вместо дефолтных паролей;
- не отключать SSL-проверку без необходимости;
- ограничить доступ к UI на уровне сети;
- хранить `.env` вне публичного репозитория;
- регулярно проверять логи worker и backend.
