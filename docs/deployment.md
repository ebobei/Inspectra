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
- `LLM_VERIFY_SSL`
- `REVIEW_PROMPT_LANGUAGE`
- `ENCRYPTION_KEY`
- `ADMIN_API_TOKEN`

## Network layout
By default only one external port is exposed:

- `UI_PORT` → nginx + React UI

The backend API is not exposed directly. nginx proxies `/api` to the internal `api:8000` service.
PostgreSQL and Redis stay inside the Docker Compose network.

This is intentional. Do not expose database or Redis ports for the normal pilot path.

## Smoke verification
1. `GET http://localhost:18080/api/health` returns `database=ok` and `redis=ok`
2. Admin UI opens at `http://localhost:18080`
3. One connector can be created and tested
4. One session can be created and run
5. One publication attempt appears in the UI

## Production notes
- do not keep default secrets
- set `APP_ENV=production`
- restrict network access to the admin UI
- set `WEBHOOK_SHARED_SECRET` before exposing webhook routes
- keep expectations narrow: this is an internal tool, not a public SaaS surface
