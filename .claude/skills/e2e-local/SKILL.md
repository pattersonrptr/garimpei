---
name: e2e-local
description: Run Garimpei's end-to-end check against the local Docker Compose stack - rebuild the changed services, start what is stopped and wait for the API, site, admin and Mailpit to answer, run the Playwright suite in Playwright's Chromium, and take mobile and desktop screenshots. Use before asking for a merge of any user-facing change, or when the author asks to "rodar o e2e", "testar ponta a ponta" or for prints.
---

# Local end-to-end check

Step 3 of the working agreement ("verify before asking for a merge"). Run it
from the repository root. Report the result honestly: pass/fail counts, the
failing test names, and the screenshot paths.

## 1. Rebuild what changed

| Changed | Command |
|---|---|
| `backend/` | `docker compose restart web` (uvicorn `--reload` misses changes on the Windows bind mount) |
| `web/` | `docker compose up -d --build site` |
| `frontend/` | `docker compose up -d --build frontend` |
| `scrapers/` | `docker compose up -d --build scraper celery-beat` |

Trap: `up --build site` (or `frontend`) **also restarts `web`**. Always run
step 2 after any rebuild, or sign-in and sign-up fail in the tests.

## 2. Preflight

```bash
bash .claude/skills/e2e-local/preflight.sh
```

It starts the services the suite needs that are stopped (`db`, `redis`,
`web`, `site`, `frontend`, `mailpit`; without Mailpit the e-mail tests
fail), waits (up to 3 min) until the API `:8000`, the site `:3000`, the
admin `:80` and Mailpit `:8026` answer, and says which one did not. Then it
runs `npx playwright install chromium` in `frontend/` (a no-op when already
installed; after a Playwright update, every test fails on launch without
it). With `E2E_CHANNEL` set it skips the install.

## 3. Run the suite

From `frontend/`:

```bash
npx playwright test --project=chromium
```

- Uses Playwright's own Chromium on any OS (installed by the preflight).
  `E2E_CHANNEL=chrome` or `msedge` uses an installed browser instead.
- Accounts come from the `E2E_*` values in `.env` (read by
  `e2e/fixtures.ts`; never print them). E-mails land in Mailpit
  (`http://localhost:8026`).
- On failure, open the screenshot in `frontend/test-results/` before
  guessing: selectors must use the real labels (Next's route announcer also
  has `role="alert"`, so select form errors by `.form-error`).
- Throwaway users created by a failed run: list them and ask the author
  before deleting anything from the dev database.

## 4. Screenshots (mobile and desktop)

From `frontend/` (it uses this folder's Playwright):

```bash
node ../.claude/skills/e2e-local/screenshots.mjs <out-dir> / /busca?q=duna
node ../.claude/skills/e2e-local/screenshots.mjs --login <out-dir> /alertas /conta
```

- In Git Bash, prefix the command with `MSYS_NO_PATHCONV=1`, or `/alertas`
  becomes a Windows path.
- One PNG per page and size (390×844 and 1366×900), full page.
- `--login` signs in on the site as `E2E_USER_USERNAME` first.
- Write to the session scratchpad, not the repository. Look at every image
  before reporting; mention anything that looks broken.
