# Backend layout: one module per domain

Decision record, Nov 2026 (price comparator plan, Phase 1a).

## Decision

The backend is organized by **domain module**, not by technical layer. Inside a
module, the layers still exist and the dependency rule still holds (arrows point
inward), but the folder name says what the code is about.

```text
backend/src/app/
  catalog/                 products and price history (done)
    entities.py            plain dataclasses, no framework imports
    rules.py               validation rules
    ports.py               repository interfaces, owned by the use cases
    use_cases.py
    persistence/           SQLAlchemy models and repositories
    http/                  controllers, presenters, request/response schemas
  alerts/ accounts/ billing/ ...   moved one per PR, behavior unchanged
  shared/                  database, middleware, security (when needed)
```

Old layer folders (`entities/`, `use_cases/`, `infrastructure/`, `interfaces/`)
shrink as modules move and are removed when empty.

## Rules

- `entities.py`, `rules.py`, `ports.py` and `use_cases.py` import no
  FastAPI, SQLAlchemy or Pydantic. Pydantic stays in `http/` and in settings.
- A port is shaped by what the use case needs, not by what the database offers.
- Each move is a small PR with no behavior change, protected by the existing
  tests. Run the whole suite before and after.
- Tests stay where they are for now; they only get their imports updated.

## Status

| Module | State |
|---|---|
| `catalog` | Moved. Entities are dataclasses. |
| `alerts` (alerts, notifications, evaluation) | Next |
| `accounts` (users, auth), `billing` (plans, subscriptions) | Later |
| search configs, source websites, execution logs | Later; module name to decide |

Known leftover: `http/` inside `catalog` keeps one file per concept
(`product_controller.py`, `price_history_controller.py`, ...) because each
controller owns its own router.
