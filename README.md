# Inspectra

## English summary

Inspectra is a self-hosted tool for AI-assisted review of Jira issues, merge requests and other development artifacts.

It is designed for internal corporate use and can work with both external LLM APIs and local LLM-compatible endpoints.

The main purpose of Inspectra is to analyze a development artifact and maintain a single managed AI review comment in the source system.

---

## О проекте

Inspectra — self-hosted инструмент для AI-review задач Jira, merge request'ов и других артефактов разработки.

Система помогает находить проблемы в требованиях, задачах, описаниях изменений и технических артефактах до того, как они попадут в разработку, тестирование или релиз.

Основной сценарий работы:

1. Inspectra получает данные из исходной системы.
2. Выполняет анализ с помощью LLM.
3. Формирует структурированный результат review.
4. Публикует результат обратно в исходную систему.
5. При повторном запуске обновляет ранее созданный управляемый комментарий, а не создаёт новый каждый раз.

Проект рассчитан на запуск внутри инфраструктуры организации и не требует SaaS-модели.

---

## Для чего нужен Inspectra

Inspectra полезна в командах, где задачи, требования и изменения часто проходят review вручную и качество входных артефактов сильно влияет на дальнейшую разработку.

Типовые сценарии:

- предварительная проверка задач Jira перед передачей в разработку;
- поиск противоречий, неясностей и пропущенных требований;
- анализ merge request'ов и связанных описаний изменений;
- дополнительный контроль качества требований перед реализацией;
- помощь QA, аналитикам, разработчикам и тимлидам при review рабочих артефактов.

Inspectra не заменяет человека, но помогает быстрее находить слабые места в описаниях задач и изменений.

---

## Ключевая идея

Inspectra поддерживает один управляемый AI-комментарий для одной исходной сущности.

Это значит, что при повторном анализе одной и той же задачи или merge request'а система не засоряет исходную систему множеством новых комментариев.

Вместо этого Inspectra:

- находит ранее опубликованный AI-комментарий;
- обновляет его актуальным результатом;
- создаёт комментарий заново, если он был удалён вручную;
- не выполняет лишнюю публикацию, если исходные данные не изменились.

Такой подход позволяет использовать AI-review регулярно, не превращая Jira или другую source-систему в поток одноразовых комментариев.

---

## Возможности

На текущем этапе Inspectra поддерживает:

- запуск через Docker Compose;
- backend API на FastAPI;
- frontend UI;
- nginx proxy для доступа к API через UI;
- PostgreSQL для хранения состояния;
- Redis для очереди фоновых задач;
- worker для выполнения review pipeline;
- интеграцию с Jira через REST API v2;
- вызов LLM-провайдера через HTTP API;
- публикацию AI-review обратно в Jira;
- поддержку одного управляемого комментария;
- восстановление комментария после ручного удаления;
- вынесенные prompt-файлы;
- русский review prompt по умолчанию;
- настройку проверки SSL для LLM API;
- базовую обработку ошибок UI и backend.

---

## Как это работает

Упрощённая схема:

```text
Browser
  |
  v
UI / nginx
  |
  +-- /api/* --> backend API
                  |
                  +-- PostgreSQL
                  +-- Redis
                  +-- worker
                         |
                         +-- Jira
                         +-- LLM provider
```

Состав сервисов:

```text
ui        - frontend и nginx proxy
api       - backend API
worker    - фоновый обработчик review-задач
postgres  - база данных
redis     - очередь задач
```

Наружу публикуется только один порт — UI/nginx.

API доступен через nginx proxy по пути `/api`.

---

## Быстрый старт

### 1. Подготовить `.env`

Создайте `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 2. Заполнить настройки Jira и LLM

Минимальный набор переменных:

```env
JIRA_BASE_URL=https://jira.example.com
JIRA_USERNAME=user@example.com
JIRA_API_TOKEN=your-token

LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

Если используется локальный LLM gateway или Ollama-compatible endpoint, укажите соответствующий `LLM_BASE_URL` и модель.

### 3. Запустить проект

```bash
docker compose up --build
```

После запуска UI будет доступен по адресу:

```text
http://localhost:18080
```

API documentation:

```text
http://localhost:18080/api/docs
```

Health check:

```text
http://localhost:18080/api/health
```

---

## Настройка порта

По умолчанию Inspectra использует внешний порт:

```env
UI_PORT=18080
```

Если порт занят, измените его в `.env`:

```env
UI_PORT=19080
```

После изменения порта перезапустите контейнеры:

```bash
docker compose down
docker compose up --build
```

---

## Основные переменные окружения

### Общие

```env
APP_ENV=local
UI_PORT=18080
```

`APP_ENV` задаёт окружение запуска.

`UI_PORT` задаёт внешний порт UI/nginx.

---

### PostgreSQL

```env
POSTGRES_DB=inspectra
POSTGRES_USER=inspectra
POSTGRES_PASSWORD=inspectra
DATABASE_URL=postgresql+psycopg://inspectra:inspectra@postgres:5432/inspectra
```

PostgreSQL используется для хранения состояния review-сессий, запусков, комментариев и связанных данных.

База данных не публикуется наружу отдельным портом.

---

### Redis

```env
REDIS_URL=redis://redis:6379/0
```

Redis используется как очередь для фоновой обработки задач.

Redis не публикуется наружу отдельным портом.

---

### Jira

```env
JIRA_BASE_URL=https://jira.example.com
JIRA_USERNAME=user@example.com
JIRA_API_TOKEN=your-token
```

`JIRA_BASE_URL` — адрес Jira.

`JIRA_USERNAME` — пользователь Jira.

`JIRA_API_TOKEN` — токен или пароль для авторизации.

---

### LLM

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
LLM_VERIFY_SSL=true
```

`LLM_BASE_URL` — базовый URL LLM API.

`LLM_API_KEY` — ключ доступа к LLM API.

`LLM_MODEL` — имя модели.

`LLM_VERIFY_SSL` управляет проверкой SSL-сертификатов при обращении к LLM API.

В корпоративных сетях с внутренними сертификатами можно временно отключить проверку SSL:

```env
LLM_VERIFY_SSL=false
```

Отключение SSL-проверки снижает безопасность и должно использоваться осознанно.

---

### Prompt

```env
REVIEW_PROMPT_LANGUAGE=ru
```

Prompt-файлы находятся в директории:

```text
backend/app/prompts/
```

Основные файлы:

```text
review_system.ru.txt
review_user.ru.txt
```

Prompt вынесен из кода, чтобы его можно было редактировать без изменения backend-логики.

---

## Review pipeline

Типовой lifecycle review:

```text
создание review session
  |
  v
запуск run
  |
  v
постановка задачи в очередь
  |
  v
получение данных из source-системы
  |
  v
вызов LLM
  |
  v
нормализация результата
  |
  v
публикация или обновление managed comment
```

---

## Managed AI comment

Inspectra публикует в source-систему управляемый комментарий.

Ожидаемое поведение:

| Ситуация | Поведение |
|---|---|
| Комментария ещё нет | создать новый managed comment |
| Комментарий уже есть | обновить существующий |
| Комментарий удалён вручную | создать новый managed comment |
| Исходные данные не изменились | не выполнять лишнюю публикацию |
| LLM вернула неполные данные | обработать безопасно и не ломать весь run |

---

## Prompt-файлы

Review prompt хранится в обычных текстовых файлах:

```text
backend/app/prompts/review_system.ru.txt
backend/app/prompts/review_user.ru.txt
```

Это позволяет:

- редактировать prompt без изменения Python-кода;
- версионировать prompt вместе с проектом;
- видеть изменения prompt'а в Git;
- не усложнять систему отдельным prompt registry или хранением prompt'ов в БД.

---

## Безопасность

Inspectra может работать с чувствительными корпоративными данными:

- задачами Jira;
- требованиями;
- описаниями дефектов;
- внутренними комментариями;
- merge request'ами;
- техническими деталями реализации.

Перед использованием внешнего LLM API необходимо убедиться, что это допустимо внутренними правилами организации.

Для чувствительных данных предпочтительнее использовать:

- локальную LLM;
- корпоративный LLM gateway;
- self-hosted inference endpoint;
- маскирование чувствительных данных перед отправкой в модель.

---

## Ограничения

Inspectra сфокусирована на AI-review артефактов разработки и публикации управляемого комментария обратно в исходную систему.

Проект не предназначен для замены Jira, GitLab, Confluence или полноценной системы управления требованиями.

Inspectra также не является SaaS-платформой: предполагаемый сценарий использования — self-hosted запуск внутри инфраструктуры организации.

---

## Разработка

Проверка Docker Compose:

```bash
docker compose config
```

Запуск backend-тестов внутри контейнера:

```bash
docker compose run --rm api pytest
```

Пересборка контейнеров:

```bash
docker compose down
docker compose up --build
```

Полная очистка volume с данными:

```bash
docker compose down -v
```

Команда `docker compose down -v` удаляет данные PostgreSQL volume. Используйте её только если действительно нужно очистить локальное состояние.

---

## Лицензия

См. файл `LICENSE`.
