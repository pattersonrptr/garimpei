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
| Alerts users through its own port | #158 | Inappropriate Intimacy → Extract Interface + adapter | `AlertOwnerReader` + `AlertOwner(id, email)`; `UserAccountOwners` adapts the old user repository at four wiring points. No test changed |
| Alerts e-mail through its own port | #159 | Inappropriate Intimacy → Extract Interface + adapter | `AlertMailer` + `MailResult(success, error_message)`; `EmailServiceMailer` adapts the old e-mail service at four wiring points (FastAPI still injects `get_email_service`, so the e2e overrides keep working). Same method and arguments, so no test changed; inverting the adapter's result fails 4 e2e tests |
| SearchConfig characterization tests | #160 | — | Coverage was 100% but 5 of 14 mutations survived; 4 tests pin reactivation (stores and frequency from the alert) and relinking (store change relinks, store order does not). The fifth is equivalent for valid input. Approved by the author |
| Alerts SearchConfig through its own port | #161 | Inappropriate Intimacy → Extract Interface + adapter | `KeywordSearches` + `KeywordSearch` (a dataclass) in alerts; `SearchConfigKeywordSearches` maps to the old pydantic entity and reads before updating, so preferred time and metadata survive. Alerts' domain core no longer imports `src/app/interfaces` or `src/app/entities`. No existing test changed; the adapter had no coverage (4 of 5 mutations survived the e2e suite), so 6 integration tests were added for the author's review |
| Alerts request validator out of the domain | #162 | Divergent Change → Move Class | `alerts/rules.py` → `alerts/http/validators.py`, unchanged: `PriceAlertValidator` returns `JsonApiError`, so it is request validation, like catalog's in #154. Already covered (15 unit tests plus e2e); only the test's import line changed, approved by the author like #154 |
| Catalog stops wiring alerts' adapters | (this PR) | Inappropriate Intimacy → Move Function | `alerts/wiring.py` builds `EvaluateBookAlertsUseCase` and `EvaluateProductAlertsUseCase` from the request's session and e-mail service; catalog's offer and product controllers call it and no longer import alerts' adapters or repositories. FastAPI still injects `get_db` and `get_email_service`, so the e2e overrides keep working. No test changed |

## Queue

Found while doing the slices above; each one is proposed to the author
before it starts.

- The `source_website_repo`, `user_repo`, `email_service` and
  `search_config_repo` parameters now hold alerts' ports; rename them
  (`stores`, `owners`, `mailer`, `searches`) together with the tests, which
  also call the private `_find_or_create_search_config` helpers (needs the
  author's OK).
- `catalog/persistence/repositories.py` imports alerts' ORM models.
- Alerts' use cases take catalog's repository interfaces (`catalog/ports.py`)
  instead of alerts-owned ports, so `alerts/wiring.py` builds catalog's
  repositories and catalog's controllers import alerts' use case types: a
  two-way dependency that existed before #163 (architecture-reviewer, Nov 12).
  An alerts-owned product reader (like `ProductSnapshotReader`) would break
  it, or the factories could move to a shared composition root.
- Alerts' own controller (`price_alert_controller.py`) still wires its
  adapters by hand at four points; it could use `alerts/wiring.py` too.
- Catalog controllers build concrete repositories and use cases themselves;
  that wiring belongs in FastAPI dependencies or a composition root.
- Validator tests live in `tests/unit/domain/validators/` but the code is
  now http-layer.
- Checks that need a repository (unique URL, product exists) may belong in
  the use cases rather than in request validation.
- mypy: 271 errors in 44 files outside the blocking list (#153); add paths
  to the blocking step as each area is fixed.
