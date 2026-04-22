# Deployment

## Supported startup path
```bash
cp .env.example .env
docker compose up --build
```

This repository currently supports one honest local deployment path: Docker Compose.

## Required configuration
- `DATABASE_URL`
- `REDIS_URL`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `ENCRYPTION_KEY`
- `ADMIN_API_TOKEN`

## Smoke verification
1. `GET /api/health` returns `database=ok` and `redis=ok`
2. Admin UI opens at `http://localhost:8080`
3. One connector can be created and tested
4. One session can be created and run
5. One publication attempt appears in the UI

## Production notes
- do not keep default secrets
- set `APP_ENV=production`
- restrict network access to the admin UI and API
- set `WEBHOOK_SHARED_SECRET` before exposing webhook routes
- keep expectations narrow: this is an internal tool, not a public SaaS surface
