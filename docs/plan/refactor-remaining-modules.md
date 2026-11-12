# Refactor remaining modules

Runs between other phases, one small PR per slice, behavior unchanged
(`AGENTS.md`, *Architecture rules* and *Tests first*). Untested code gets
characterization tests first, in their own PR, reviewed by the author.

## Done

| Slice | PR | Smell → refactoring | Notes |
|---|---|---|---|
| Catalog request validators out of the domain | #154 | Divergent Change → Move Class | `catalog/rules.py` imported `catalog/http/product_schema`; its validators check JSON:API request shape, so they moved to `catalog/http/validators.py`. Already covered (22 unit tests, 97% of branches, plus e2e), so no characterization tests; the author approved changing only the two tests' import line (Nov 12, 2026) |
| Alerts characterization tests | #156 | — | Before moving alerts off `src/app/interfaces`: 5 tests where those dependencies were used and uncovered (store lookup once per store, "Unknown" store, listing without price skipped, book alert never links a SearchConfig, update validator 404 for a missing store). Approved by the author |
| Alerts stores through its own port | #157 | Inappropriate Intimacy → Extract Interface (port owned by the client) + adapter | `StoreReader` + `Store` in alerts; `SourceWebsiteStores` adapts the old repository at four wiring points. Parameter names kept, so no test changed |

## Queue

Found while doing the slices above; each one is proposed to the author
before it starts.

- `alerts/use_cases.py` still imports from the older `src/app/interfaces`
  package: users, e-mail and search configs (stores done in #157). One
  alerts-owned port per PR, like `StoreReader`.
- `alerts/rules.py` holds `PriceAlertValidator`, which returns
  `JsonApiError`: request validation, like catalog's before #154.
- The `source_website_repo` parameters now hold a `StoreReader`; rename to
  `stores` together with the tests (needs the author's OK).
- Catalog controllers import alerts' adapters to wire alerts use cases; an
  alerts-owned wiring module would hide them.
- Catalog controllers build concrete repositories and use cases themselves;
  that wiring belongs in FastAPI dependencies or a composition root.
- Validator tests live in `tests/unit/domain/validators/` but the code is
  now http-layer.
- Checks that need a repository (unique URL, product exists) may belong in
  the use cases rather than in request validation.
- mypy: 271 errors in 44 files outside the blocking list (#153); add paths
  to the blocking step as each area is fixed.
