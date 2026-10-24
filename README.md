# 🏴‍☠️ Garimpei — Opportunity Hunter

> Development name: `product-tracker`

A price monitoring and opportunity detection system for Brazilian marketplace
resellers. Automatically tracks product prices across multiple e-commerce
platforms (OLX, Mercado Livre, Enjoei, Estante Virtual), sends email alerts
when products drop below target prices, and provides a dashboard to manage
alerts and discover opportunities.

| Service | Tech | Directory |
|---|---|---|
| **Backend** | FastAPI · SQLAlchemy · Alembic · PostgreSQL | [`backend/`](backend/README.md) |
| **Scrapers** | Celery · Playwright · BeautifulSoup · Redis | [`scrapers/`](scrapers/README.md) |
| **Frontend** | React 19 · Vite · MUI · TypeScript | [`frontend/`](frontend/README.md) |

---

## Features

- 🔎 **Multi-marketplace scraping** — OLX, Mercado Livre, Enjoei, Estante Virtual
- 🎯 **Price alerts** — set a target price per product; get notified when it drops
- 📬 **Email notifications** — via SendGrid, with rate limiting and dedup
- ⏱️ **Scheduled & on-demand checks** — frequency-based scheduling + manual trigger
- 📊 **Dashboard** — manage alerts, track history, discover opportunities
- 👤 **Admin dashboard** — user and system management
- 💳 **Freemium model** — plans, subscriptions and usage limits
- 🧪 **Tested** — unit tests + Playwright E2E, CI on GitHub Actions

---

## Quick Start

```bash
# Clone
git clone https://github.com/pattersonrptr/product-tracker.git
cd product-tracker

# Copy env file and adjust as needed
cp .env.example .env

# Start everything
make up

# Or without Make:
docker compose up --build
```

The services will be available at:

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Frontend | http://localhost |
| Flower (Celery monitor) | http://localhost:5555 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## Development

```bash
# Run only infrastructure (db + redis)
make infra

# Backend dev server (outside Docker)
make backend-dev

# Frontend dev server (outside Docker)
make frontend-dev

# Run all tests
make test

# Run tests for a specific service
make backend-test
make scrapers-test
make frontend-test

# Lint
make lint
```

See the [`Makefile`](Makefile) for all available commands.

---

## Architecture

```
┌──────────┐       HTTP        ┌──────────┐       SQL        ┌──────────┐
│ Frontend │ ───────────────▶  │ Backend  │ ───────────────▶  │ Postgres │
│ (React)  │                   │ (FastAPI)│                   │          │
└──────────┘                   └────┬─────┘                   └──────────┘
                                    │ HTTP
                               ┌────┴─────┐
                               │ Scrapers │       broker      ┌──────────┐
                               │ (Celery) │ ◀───────────────  │  Redis   │
                               └──────────┘                   └──────────┘
```

- **Frontend** consumes the backend REST API (JSON:API spec).
- **Scrapers** are Celery workers that communicate with the backend
  exclusively via HTTP — no shared database access.
- **Backend** owns the database and exposes all data through the API.
- **Alert flow:** User creates PriceAlert → system schedules scraping →
  scraper finds products → backend evaluates prices → sends email notification
  if price ≤ target → user sees opportunity on dashboard.

---

## Project Structure

```
product-tracker/
├── backend/          ← FastAPI application + database
├── scrapers/         ← Celery workers + web scraping engines
├── frontend/         ← React SPA
├── docker-compose.yml
├── Makefile
├── .github/workflows/ci.yml
└── PLAN.md           ← Reorganization plan
```

---

## Status & usage

Active personal project, still evolving (already functional). Built as an
educational/portfolio project for personal use — scraping targets public
marketplace listings; respect each platform's Terms of Service before any
non-personal use.

---

## License

MIT
