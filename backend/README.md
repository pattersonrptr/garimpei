# Garimpei — backend

FastAPI API behind the public site (`web/`), the admin (`frontend/`) and the
collectors (`scrapers/`). PostgreSQL through SQLAlchemy and Alembic, JSON:API
responses, JWT auth. Part of [Garimpei](../README.md), a price comparator for
Brazil; books are the first category.

## What it does

- **Catalog:** products (books by ISBN, metadata from BrasilAPI), offers from
  each store, new and used, and the daily price history.
- **Verdict:** "good price / wait" from the history of each product
  (`catalog/verdict.py`).
- **Alerts:** a user watches a product with a target price; when an offer
  reaches it, an e-mail goes out (SMTP/Mailpit in dev, SendGrid in prod) and
  the notification is logged.
- **Users and plans:** sign up, login, account, plan limits; admin summary
  and cleanup.

## Layout

New code follows the [screaming layout](../docs/architecture/screaming-layout.md):
one folder per domain module.

```
src/
  main.py                FastAPI app: middleware, routers, error handlers
  config/                settings (env vars) and logging
  common/jsonapi/        JSON:API response helpers
  app/
    catalog/             products, offers, price history, verdict, ISBN, matching
    alerts/              price alerts, notification text, notification log
      entities.py        pure dataclasses
      use_cases.py       application rules
      ports.py           interfaces this module needs (owned by the client)
      http/              controllers, schemas, presenters
      persistence/       ORM models, repositories, adapters over other modules
    security/            JWT auth
    entities/ use_cases/ interfaces/ infrastructure/ domain/
                         older layered code (users, plans, stores, search
                         configs); moved into modules one small PR at a time
  scripts/               one-off commands (see below)
  tests/                 unit/, integration/, e2e/ (HTTP against a test DB)
alembic/versions/        migrations (add a new one; never rewrite one on main)
seeds/                   seed ISBN list (best sellers)
```

Rules: entities have no ORM or framework imports; a module that needs another
defines the port itself and an adapter implements it (e.g. `alerts` →
`ProductSnapshotReader` over `catalog`). Details and the catalog model are in
[`docs/architecture/`](../docs/architecture/README.md).

## API

Interactive docs at `http://localhost:8000/docs` when the stack is up. Main
groups:

| Prefix | For | Auth |
|---|---|---|
| `/books` | public search, product page, offers, price history, verdict | none |
| `/auth` | register, login, refresh, verify, `/auth/me` | — |
| `/me` | the signed-in user's alerts | user |
| `/price-alerts`, `/notification-logs` | alert CRUD, notify, history | user (own) / admin |
| `/offers` | collectors post offers by ISBN; `collection-queue` lists what to collect | staff (collector) |
| `/products`, `/price-histories` | catalog management | admin |
| `/source-websites`, `/search-configs`, `/search-execution-logs` | stores and the older keyword searches | admin |
| `/users`, `/plans`, `/subscriptions`, `/admin`, `/dashboard` | users, plans, admin summary | user / admin |

Errors: bad login 400; no token, expired or invalid token 401; a valid token
without permission 403. Timestamps are naive UTC.

## Run

The usual way is the whole stack from the repository root:

```bash
docker compose up -d --build web     # API on :8000, with db, redis, mailpit
docker compose restart web           # after backend edits (Windows bind mount misses --reload)
```

On start, `start.sh` waits for the database, runs `alembic upgrade head`,
creates the dev users and stores (`scripts/init_dev_db.py`) and starts uvicorn.
Settings come from the root `.env` (see `.env.example`): `DATABASE_URL`,
`SECRET_KEY`, `EMAIL_BACKEND` (`smtp` or `sendgrid`), `SMTP_*`, `FROM_EMAIL`,
`SITE_URL`, `CELERY_*`.

## Verify

From `backend/`:

```bash
poetry install                     # once
poetry run pytest src/tests        # ~910 tests
poetry run ruff check src
poetry run ruff format --check src
```

The same commands work on Linux, macOS, BSD and Windows, and CI runs them
too. Without Poetry installed, `uvx poetry@2` works in its place. mypy blocks
CI on the paths listed in `.github/workflows/ci.yml` and only reports on the
rest. Pre-commit runs ruff and ruff-format on commit.

## Migrations

```bash
docker compose exec web alembic revision --autogenerate -m "what changed"
docker compose exec web alembic upgrade head
```

Review the generated file before committing. A migration already on `main` is
never edited: add a new one.

## Scripts

Run from `backend/` (or inside the `web` container):

| Command | What it does |
|---|---|
| `python -m src.scripts.add_book <isbn>` | find or create a book from its ISBN |
| `python -m src.scripts.load_seed_books` | load the seed ISBN list into the catalog (safe to rerun) |
| `python src/scripts/create_superuser.py` | create an admin user (interactive or with flags) |
| `python src/scripts/init_dev_db.py` | dev users, stores and fixtures (runs on start) |
