# Garimpei — working agreement for AI coding agents

Read by any agent that supports `AGENTS.md` (Codex, Copilot, Cursor, …).
Claude Code reads it through `CLAUDE.md`, which imports this file.

Garimpei is a **general price comparator** for Brazil: new and used offers
side by side, a "good price / wait" verdict, and alerts. **Books are only the
first category**; names and screens stay generic (product, user), never
"reader". No commercial launch is planned yet: the goal is a product that
works for the author first and is ready for other users.

The author decides product and architecture; the agent proposes, implements
and verifies. When in doubt about intent, ask a short round of questions.

## Repository map

| Folder | What it is |
|---|---|
| `backend/` | FastAPI + SQLAlchemy + Alembic, JSON:API responses. Domain modules under `src/app/<module>/` (`catalog`, `alerts`, …); older code still in `src/app/interfaces`, `entities`, `infrastructure` |
| `scrapers/` | Celery workers that collect offers from stores and post them to the backend |
| `web/` | **Public site** (Next.js 16, App Router): search, product pages, sign in, "my alerts", account. Everything a user does lives here |
| `frontend/` | **Admin back office only** (Vite + React + MUI). Non-admins are sent to the site |
| `docs/plan/` | Main plan (`README.md`) and one file per phase, with decisions |
| `docs/architecture/` | Architecture decisions (screaming layout, catalog model) |

## Architecture rules

- **Screaming architecture:** code is grouped by domain module, not by
  technical layer. New backend code goes into a module
  (`src/app/<module>/{entities,use_cases,http,persistence}.py`).
- **Ports belong to their client:** a module that needs something from
  another defines the interface (port) itself; the adapter implements it
  over the other module (e.g. `alerts` → `ProductSnapshotReader`, adapter
  over `catalog`).
- **Entities are pure dataclasses:** no ORM, no framework imports.
- **Refactor in small steps:** one module per small PR, behavior unchanged,
  never a big-bang rewrite.
- The web site renders on the server; client JavaScript only where needed
  (Server Actions with `useActionState` for forms).

## How we work

1. **Plan first.** Non-trivial work starts with a plan (plan mode or a doc in
   `docs/plan/`), with the author's answers to open questions recorded as
   decisions.
2. **One slice per PR, one branch per slice** (`phase-5c/my-alerts`).
3. **Verify before asking for a merge:** unit tests, type checks, build, and
   for user-facing changes an end-to-end run against the local compose stack
   with screenshots (mobile and desktop).
4. **Merge only with the author's explicit OK and a green CI.** Squash merge.
   Approval for one PR never carries over to the next.
5. **Keep the plan current:** mark slices done in the phase doc, add new
   decisions there.
6. Commit messages end with a `Co-Authored-By:` line naming the agent and
   model; PR bodies say which tool generated them.
7. Flag anything that grows the scope; propose, don't just do it.
8. `docs/working-with-ai.md` (and its `.en.md` translation) is
   written in the author's voice. When a change makes it stale (new
   protection layer, test counts, a decision, something the author learned),
   say so and propose the edit; change it only after the author reviews it.

## Verify

| Module | Commands (from the module folder) |
|---|---|
| backend | `.venv/Scripts/python -m pytest src/tests` · `.venv/Scripts/ruff check src` · `.venv/Scripts/ruff format --check src` (CI uses Poetry; mypy is non-blocking) |
| scrapers | `poetry run pytest src/tests` · `poetry run ruff check src` |
| web | `npm test` · `npm run typecheck` · `npm run build` |
| frontend | `npm run lint` · `npm test` · `npx tsc -b` |

**End to end (local):** `docker compose up -d --build <service>`, wait until
`:8000`, `:3000` and `:80` answer, then from `frontend/`:
`E2E_CHANNEL=msedge npx playwright test --project=chromium`. Test accounts
are `E2E_*` in `.env`; e-mails land in Mailpit (`http://localhost:8026`).

Local addresses: site `http://localhost:3000`, admin `http://localhost`
(port 80), API `http://localhost:8000`, Mailpit `:8026`, dev DB on `:5434`.

## Known traps

- **Windows bind mount:** uvicorn `--reload` misses changes; run
  `docker compose restart web` after backend edits.
- `docker compose up --build site` (or `frontend`) **also restarts `web`**:
  wait for `:8000` before running e2e tests.
- **Line endings:** files mix CRLF and LF. Keep each file's own endings when
  editing with scripts.
- Next.js has its own `role="alert"` route announcer: select form errors by
  class (`.form-error`), not by role.
- Intl currency formatting uses a no-break space (`R$ 18,00`).
- The backend sends naive UTC timestamps; parse them as UTC.
- API errors: bad login 400, no token 403, expired/invalid token 401.

## Never

- Edit `.env` (`.env.example` is fine). Claude Code enforces this with a hook
  and a permission rule (`.claude/`).
- Rewrite an Alembic migration that is already on `main` (a Claude Code hook
  blocks it): add a new one.
- Scrape Amazon (contract risk; use affiliate search links instead).
- Push to `main`, merge, or run destructive commands without the author's OK.
