# Inspectra

Inspectra is a self-hosted review tool for software work artifacts.

It tracks one live review comment for a Jira issue, GitLab merge request, Confluence page, or manual text input. When the source changes, Inspectra re-checks it, carries forward prior findings, avoids re-posting resolved issues, softens repeated reminders, and updates the existing external comment instead of spamming a thread.

## Status
Inspectra is an **early-stage, usable beta** for small internal engineering teams.

Primary path:
- **Jira**

Supported secondary paths:
- **GitLab**
- **Confluence** (requires validation against your specific Confluence setup)

This repository is **not** a SaaS product, **not** a multi-tenant platform, and **not** an enterprise workflow suite.

## What this repository contains
- FastAPI backend
- PostgreSQL + Alembic migrations
- Redis + RQ worker
- Minimal React admin UI
- Adapters for Jira, GitLab, and Confluence
- Webhook-driven recheck flow

## Core behavior
1. Create a review session for an external artifact.
2. Fetch and normalize the source.
3. Run an initial review and publish one external comment.
4. On later changes, re-check the updated source.
5. Update the same external comment instead of creating a new one.
6. Stop escalating after the configured iteration limit.

## What this product is
- self-hosted
- internal engineering tool
- admin/dev console with a narrow use-case
- best suited for a small engineering team that wants one managed review comment per tracked artifact

## What this product is not
- not a SaaS
- not a multi-tenant platform
- not an enterprise workflow suite
- not a generic plugin framework
- not a replacement for Jira/GitLab/Confluence

## Limitations
- security minimum only; no RBAC or SSO
- admin token is stored in browser localStorage for the current admin UI
- no multi-user audit model
- no advanced policy engine or team-specific workflow layer
- no live vendor sandbox integration suite in CI
- Confluence support is implemented but must be validated against your specific Confluence setup before broader rollout

## Quick start
```bash
cp .env.example .env
# set ENCRYPTION_KEY, ADMIN_API_TOKEN, WEBHOOK_SHARED_SECRET and LLM credentials

docker compose up --build
```

Open:
- Admin UI: `http://localhost:18080`
- API docs: `http://localhost:18080/api/docs`

Before using the admin UI, open **Settings** and paste the same `ADMIN_API_TOKEN` value there.

## Smoke start checklist
1. Open `http://localhost:18080/api/health` and confirm database + redis are both `ok`.
2. Open `http://localhost:18080` and set `ADMIN_API_TOKEN` in **Settings**.
3. Create one connector.
4. Create one session.
5. Run the session and confirm that a publication attempt appears in the UI.

## Runtime expectations
- `docker compose up --build` is the supported local startup path.
- Only the UI/nginx port is exposed by default. Backend, PostgreSQL and Redis stay inside the Docker Compose network.
- In `APP_ENV=production`, the backend refuses to start with default `ENCRYPTION_KEY` or `ADMIN_API_TOKEN`.
- `/api/health` checks API, database, and Redis availability.

## Documentation
- `docs/review-lifecycle.md`
- `docs/deployment.md`
- `docs/connectors.md`
- `SECURITY.md`

## Development and verification
- backend unit tests: `pytest backend/tests -q`
- frontend build: `cd ui && npm ci && npm run build`
- compose config check: `docker compose config`


## Review prompt
The default review prompt is stored in files instead of being hardcoded in Python:

- `backend/app/prompts/review_system.ru.txt`
- `backend/app/prompts/review_user.ru.txt`

`REVIEW_PROMPT_LANGUAGE=ru` is the default. Keep this simple: edit the files when the pilot needs prompt changes. Do not introduce prompt profiles or a database-backed prompt editor until there is a real operational need.
