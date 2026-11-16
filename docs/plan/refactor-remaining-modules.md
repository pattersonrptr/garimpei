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
| Catalog stops wiring alerts' adapters | #163 | Inappropriate Intimacy → Move Function | `alerts/wiring.py` builds `EvaluateBookAlertsUseCase` and `EvaluateProductAlertsUseCase` from the request's session and e-mail service; catalog's offer and product controllers call it and no longer import alerts' adapters or repositories. FastAPI still injects `get_db` and `get_email_service`, so the e2e overrides keep working. No test changed |
| Alerts-owned Listings port and its adapter | #164 | Inappropriate Intimacy → Extract Interface (port owned by the client) + adapter, step 1 | `Listings` + `Listing` (a frozen dataclass) in alerts; `CatalogListings` adapts catalog's `ProductRepository`. 12 integration tests approved by the author (Nov 12, 2026), red then green. Not wired yet: the notification use cases move to it one PR each, showing the author the mock-setup diff first. `GetProductsByPriceAlertUseCase` stays on catalog's repository: it lists full catalog products for a catalog presenter (own queue item) |
| SendPriceAlertNotification through Listings | #165 | Inappropriate Intimacy → Change the dependency to the client-owned port | The use case asks `Listings.cheapest_match` for the best match instead of catalog's `search_by_term_and_sources(limit=1)`; `POST /price-alerts/{id}/notify` wires `CatalogListings`. Test diff (mock setup and one interaction assertion: `cheapest_match` with the alert's term, stores and max price) approved by the author before the change. Red was a `ValueError` (old code unpacking the new mock), not an assertion: inherent to swapping a port. `listings.py` added to the blocking mypy paths |
| EvaluateProductAlerts through Listings | #166 | Inappropriate Intimacy → depend on the client-owned port | `Listings.get_by_id` brings the listing with its latest price, so the use case no longer needs catalog's price history repository; `alerts/wiring.py` builds `CatalogListings`. Test diff (mock setup only, no assertion changed) approved by the author. **Behavior change approved by the author (Nov 12, 2026):** "latest price" is now the point with the highest id, like the rest of the site, instead of the highest `created_at`; they differ only for points saved out of order. `OpportunityNotifier.notify` takes `Listing \| Product` until the last use case moves |
| NotifyAlertOpportunities and EvaluateBookAlerts through Listings | #167 | Inappropriate Intimacy → depend on the client-owned port | One PR because the first builds the second over the same repository. `opportunities_for_alert` and `available_offers_for_book` replace catalog's `get_all` + `ProductListFilters`; `OpportunityNotifier.notify` takes only `Listing`; `alerts/wiring.py` no longer imports catalog. Test diff (mock setup only) approved by the author; book alerts are covered by 12 e2e tests, unchanged |
| Characterization tests for alert products | #168 | — | 4 e2e tests for `GET /price-alerts/{id}/products` (max price on and off, cheapest first, pagination, 404); filter off had no test above the unit level. A mutation (always filter) fails 2. Approved by the author |
| Products by alert searched in catalog | #169 | Feature Envy → Move Function | `GetProductsByPriceAlertUseCase` only searched catalog's products for a catalog presenter. The alerts controller already loads the alert to check its owner, so it now calls catalog's new `SearchProductsByTermUseCase` with the alert's term, stores and max price. The 4 unit tests of the old use case were removed (covered by #168 and 1 new catalog test, approved by the author; red on an assertion). Alerts' use cases no longer import catalog |
| Port parameters named after the ports | #171 | Mysterious Name → Rename Variable | In alerts' use cases `product_repo`, `user_repo`, `source_website_repo`, `email_service` and `search_config_repo` held alerts' ports; they are now `listings`, `owners`, `stores`, `mailer` and `searches` (parameters and attributes), plus `PriceAlertValidator`'s `stores` (found by the architecture-reviewer; its tests pass it by position). Test diff (the 4 keyword names in two `_build_use_case` helpers) approved by the author; red was a `TypeError` (unexpected keyword), as expected for a rename |
| Characterization tests for the alerts controller's wiring | #172 | — | Before moving its wiring to `alerts/wiring.py`: 3 of 6 wiring mutations survived the suite (`/notify` sending through the real e-mail service, `/notify` finding no listing, delete leaving the search active). 2 e2e tests kill all three on an assertion. Approved by the author (Nov 13, 2026) |
| Alerts controller wired through `alerts/wiring.py` | #173 | Duplicated Code → Extract Function + Move Function | `price_alert_controller.py` built alerts' adapters by hand at four points (opportunities, validator, create/update/delete, notify); it now calls factories in `alerts/wiring.py` and no longer imports adapters or `src/app/infrastructure` repositories. Its four unused repository dependencies were removed. FastAPI still injects `get_db` and `get_email_service`. No test changed; #172's tests kill the wiring mutations the suite missed. `wiring.py` and the controller joined the blocking mypy paths |
| Characterization tests for the alert-match filter | #175 | — | Before removing `catalog/persistence/repositories.py`'s imports of alerts' ORM models: 2 of 8 mutations of the alert-match filter and the delete survived the suite (a deleted alert still matching, the user filter ignored). 2 e2e tests kill both on an assertion. Approved by the author (Nov 14, 2026) |
| SQLite enforces foreign keys in tests | #176 | — | Before slice B: `src/tests/conftest.py` turns on `PRAGMA foreign_keys=ON` for every SQLite connection, so test databases apply foreign keys and `ON DELETE` rules like Postgres. All 916 tests pass unchanged; deleting a notified product without clearing its log now fails with `FOREIGN KEY constraint failed`. Approved by the author (Nov 14, 2026) |
| Extra characterization tests for alert notify | #178 | — | Three cases #172 left out, from a duplicate PR (#177, closed): no match under the max price (skipped, no e-mail), a second call within the rate limit (skipped, one e-mail), unknown alert (404). Added to `test_price_alert_wiring.py`; they pass on today's code. Approved by the author (Nov 16, 2026) |
| Notification log cleared by the database | #180 | Inappropriate Intimacy → Move Function (to the schema: `ON DELETE SET NULL`) | Step B of the plan for catalog's repositories importing alerts' ORM models. `ProductRepository.delete` no longer nulls `NotificationLog.product_id` itself; migration `e5f1a7c3d904` recreates `notification_logs_product_id_fkey` with `ON DELETE SET NULL` (upgrade, downgrade and upgrade checked on a scratch Postgres database, and a deleted product left its log with a null `product_id`). Spec: the existing `test_a_notified_listing_can_still_be_deleted`, unchanged; red was an `IntegrityError` (the test client re-raises server errors), not an assertion. Catalog's repository still imports `PriceAlert` and `price_alert_source_website` (step C) |
| Alert-match filter through a catalog-owned port | #182 | Inappropriate Intimacy → Extract Interface (port owned by the client) + Move Function to the adapter | Step C. `ListingScope` in `catalog/ports.py` (returns an SQL condition, so the product list stays one query; `ports.py` now imports `sqlalchemy.ColumnElement`); `AlertListingScope` in `alerts/persistence/listing_scope.py` holds the old filter, moved unchanged; `ProductRepository(db, scope=None)` refuses the filter without a scope (1 new test, 2 cases, approved by the author Nov 16, 2026; red was "DID NOT RAISE"). `CatalogListings` passes its own scope; `GET /products` gets it from `catalog/http/listing_scope.py`, a registry filled by the new composition root `src/app/composition.py` (called in `src/main.py`). Catalog's persistence no longer imports alerts. The three new files joined the blocking mypy step |
| Catalog's controllers ask alerts through a catalog-owned port | #183 | Inappropriate Intimacy → Extract Interface (port owned by the client) + adapter | `PriceAlertChecks` (`check_book`, `check_product`) in `catalog/ports.py` and `AlertEvaluation` in `catalog/entities.py`; `CatalogAlertChecks` in `alerts/wiring.py` runs alerts' evaluation use cases; `catalog/http/price_alert_checks.py` is a registry the composition root fills with a per-request factory (db session, e-mail service). `offer_controller` and `product_controller` no longer import alerts, so catalog imports nothing from alerts. Covered before and after: a no-op at either wiring point (then in the adapter) fails 2 book-alert and 6 product-alert e2e tests. No test changed |
| Catalog's controllers wired through `catalog/wiring.py` | #184 | Inappropriate Intimacy → Move Function (construction to a factory module) | `catalog/wiring.py` builds the concrete repositories, the BrasilAPI client and the composed use cases (ingest offer, collection queue); the four controllers take catalog's ports (`ProductRepositoryInterface`, `PriceHistoryRepositoryInterface`, `BookCatalogReader`, `BookMetadataGateway`) and no longer import `catalog.persistence` or `catalog.adapters`. The controllers and `wiring.py` joined the blocking mypy step. Also, approved by the author (Nov 16, 2026): `test_evaluate_product_alerts.py` imports `get_email_service` from `src.app.infrastructure.services.email_service`, so `product_controller` drops its re-export. A mutation (`products()` dropping the scope) fails 5 e2e tests |
| Alerts' controllers stop building catalog's repository | #186 | Inappropriate Intimacy → Move Function (to `catalog/wiring.py`); Remove Dead Code | `price_alert_controller` gets catalog's products from `catalog.wiring.products(db)`, typed as `ProductRepositoryInterface`. `notification_log_controller` had four unused dependency functions (price alert, product, user and store repositories); removed, with their imports of catalog's persistence and the old `src/app/infrastructure` repositories. A mutation (the dependency returning `None`) fails 6 e2e tests of `/products` and `/opportunities`. No test changed; `notification_log_controller` joined the blocking mypy step |
| Characterization tests for accounts | (this PR) | — | Before users and login move into an `accounts` module (decided by the author, Nov 16, 2026: users, sign-up, login/tokens and the logged-in user; plans and subscriptions later in `billing`; `User` becomes a pure dataclass and the e-mail format is checked only in the request schemas). 9 e2e tests in `test_accounts_characterization.py`: public sign-up (regular user, staff rights ignored, taken username and e-mail, invalid e-mail), the logged-in user (token without a username 401, deleted user 404, deactivated user 400, today's codes) and an invalid e-mail on update (422). Three mutations (sign-up keeping staff rights, 404 → 401, inactive user let through) each fail one test. Approved by the author (Nov 16, 2026) |

## Queue

Found while doing the slices above; each one is proposed to the author
before it starts.

- Done: `catalog/persistence/repositories.py` imported alerts' ORM
  models, in two places. Plan decided by the author (Nov 14, 2026), three
  PRs:
  - **A. Characterization tests** (#175): a mutation run over the
    alert-match filter and the delete found two survivors (a deleted alert
    still matching, and the user filter ignored); one e2e test each.
    Clearing the notification log on delete was already covered.
  - **B. Notification log on product delete** (#180): a new migration
    gives `notification_logs.product_id` `ON DELETE SET NULL`, and the
    repository stops updating `NotificationLog`. SQLite only applies it
    with `PRAGMA foreign_keys=ON`; the test engines turn it on since the
    PR below (approved by the author, Nov 14, 2026).
  - **C. Alert-match filter** (#182): catalog owns a `ListingScope`
    port in `catalog/ports.py` that gives the "listings an alert found"
    condition; alerts implements it over its ORM, and catalog's HTTP layer
    gets it from a registry the composition root fills (decided by the
    author, Nov 16, 2026).
- Catalog imports nothing from alerts (#183). Alerts' adapters and
  http layer still use catalog, which is the allowed direction.
- Alerts' controller builds create/update/delete through `wiring` inside the
  handlers, but gets the validator and opportunities through `Depends`; one
  way for all would let `dependency_overrides` swap any of them (found by the
  architecture-reviewer, low priority).
- Alerts' controller uses catalog's presenter, schema and
  `SearchProductsByTermUseCase` for `/products` and `/opportunities` (allowed
  direction); since #186 it gets the repository from `catalog/wiring.py`
  as `ProductRepositoryInterface` instead of building `ProductRepository`.
- Done (#184): catalog controllers built concrete repositories and use
  cases themselves. Still open: `offer_controller` builds the old
  `SourceWebsiteRepository` (`src/app/infrastructure`), which belongs to
  whichever module ends up owning stores; handlers still build
  single-repository use cases inline from the injected port.
- Validator tests live in `tests/unit/domain/validators/` but the code is
  now http-layer.
- Checks that need a repository (unique URL, product exists) may belong in
  the use cases rather than in request validation.
- Accounts, still uncovered after the characterization PR (the author asked
  for tests later, Nov 16, 2026): `create_access_token` with an explicit
  expiry, the rollback when deleting a user fails, and the abstract
  `UserRepositoryInterface`. Also a question for the author: a deleted user's
  token answers 404 and a deactivated user 400; 401 and 403 would fit better
  (a fix, tests first).
- mypy: 271 errors in 44 files outside the blocking list (#153); add paths
  to the blocking step as each area is fixed.
