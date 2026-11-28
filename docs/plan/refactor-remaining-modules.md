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
| Characterization tests for accounts | #187 | — | Before users and login move into an `accounts` module (decided by the author, Nov 16, 2026: users, sign-up, login/tokens and the logged-in user; plans and subscriptions later in `billing`; `User` becomes a pure dataclass and the e-mail format is checked only in the request schemas). 9 e2e tests in `test_accounts_characterization.py`: public sign-up (regular user, staff rights ignored, taken username and e-mail, invalid e-mail), the logged-in user (token without a username 401, deleted user 404, deactivated user 400, today's codes) and an invalid e-mail on update (422). Three mutations (sign-up keeping staff rights, 404 → 401, inactive user let through) each fail one test. Approved by the author (Nov 16, 2026) |
| Accounts gaps covered | #188 | — | The gaps #187 left, approved by the author (Nov 16, 2026): login and refresh tokens last `ACCESS_TOKEN_EXPIRE_MINUTES` (2 e2e tests), and deleting a user who owns an alert fails with `IntegrityError` and keeps the user (1 integration test; the rollback path). Mutations (each token twice as long, delete without rollback) each fail one test. `create_access_token`'s default expiry is never used (both callers pass one): removed in the first accounts slice (Remove Dead Code). Abstract bodies (`raise NotImplementedError`) are excluded from the coverage report in `pyproject.toml` |
| Accounts slice 1: `User` is a pure dataclass | #189 | Primitive Obsession on a framework type → Move Class (to `accounts/entities.py`) + Replace Pydantic model with dataclass | `User` was a Pydantic model that validated the e-mail on every construction, reads from the database included; it is now `@dataclass(kw_only=True)` in `accounts/entities.py` with the same fields and defaults, and `entities/user.py` is gone (21 app files and a script import the new path). The e-mail format is checked only by the request schemas (decided by the author, Nov 16, 2026; #187 pins sign-up and update refusing an invalid e-mail). The old `UserRepository` maps ORM rows to the entity field by field and writes with `asdict`; the password change uses `dataclasses.replace`. Test diff (the import line in 6 test files) approved by the author; red was a `ModuleNotFoundError`, as expected for a move. `accounts/entities.py` joined the blocking mypy step |
| Accounts slice 2: persistence | #190 | Move Class (ORM model, repository and its interface into the module) | `user_model.py` → `accounts/persistence/models.py`, the old `UserRepository` → `accounts/persistence/repositories.py`, `UserRepositoryInterface` → `accounts/ports.py` (moved with `git mv`, content unchanged), and every import updated (alerts' owners and wiring, the old controllers, `security/auth.py`, validator, use cases, the model registries, two scripts). The repository's `updated_at` goes through the same assignment loop as the other fields, which clears its mypy error. Test diff (imports in 10 test files) approved by the author; red was a `ModuleNotFoundError`. The three files joined the blocking mypy step |
| Accounts slice 3: use cases take plain data | #191 | Move Function (into `accounts`) + Introduce Parameter Object (`NewUser`, `UserChanges`) | `user_use_cases.py` → `accounts/use_cases.py`; create and update take the plain dataclasses instead of the JSON:API request schemas, which translate with `to_new_user()` and `to_changes()` (decided by the author, Nov 16, 2026: JSON:API stays the HTTP contract, the core takes plain data). `user_validator.py` → `accounts/http/validators.py` (it builds JSON:API errors, so it stays http and takes the schemas). passlib's `pwd_context`, which the controllers and `create_superuser.py` took from the use cases module, → `accounts/adapters/passwords.py`. Test diff approved by the author: the use case tests build `NewUser`/`UserChanges` (no assertion changed) and the validator test's import. A mutation run over the translations found the e-mail on update uncovered over HTTP; a new e2e test (`test_a_staff_member_changes_a_users_email`, approved) kills it. Red was a `ModuleNotFoundError`. The three files joined the blocking mypy step |
| Accounts slice 4: login tokens and the logged-in user | #192 | Move Function + Extract Function + Remove Dead Code | `security/auth.py` → `accounts/http/auth.py` (typed; the other modules' http layers import the logged-in user from there, as the plan allows), and `security/` is gone. Token creation leaves `auth_controller` for `accounts/http/tokens.py`: the claims built twice (login and refresh) become `create_access_token(user)`, and its never-used default expiry is removed; `decode_access_token` keeps `jose` in one place. No test changed: the characterization tests (#187, #188) cover login, refresh, expiry and the logged-in user over HTTP; two mutations (expiry +5 minutes, `sub` = e-mail) fail them. No red, as for any move with unchanged tests. `auth.py` and `tokens.py` joined the blocking mypy step |
| Accounts slice 5a: schemas and presenters | #193 | Move Function | `user_schema`, `auth_schema`, `user_presenter` and `auth_presenter` leave `interfaces/http/` for `accounts/http/`, so `accounts/http/validators.py` no longer imports from the old layer. With the validator importing `user_schema` from inside `accounts`, the blocking mypy step began reporting two old type errors there: `ResourceObject.from_model` now returns `Self` (it builds `cls`; this also fixes the same error in catalog's and alerts' schemas, whole-backend mypy 254 → 242), and `UsersCollectionResponse.data` gets a narrow `type: ignore[assignment]` (a Pydantic field narrowed in a subclass). Test diff approved by the author (Nov 16, 2026): three imports, no assertion changed. Red was a `ModuleNotFoundError` |
| Accounts slice 5b: controllers and wiring | #194 | Move Function + Interface Segregation | `auth_controller` and `user_controller` leave `interfaces/http/controllers/` for `accounts/http/`. The new `accounts/wiring.py` builds the user repository for them and for the logged-in-user dependency, so nothing outside accounts' persistence and wiring builds `UserRepository` (except `scripts/create_superuser.py`). Alerts' `UserAccountOwners` now reads an owner through accounts' `GetUserByIdUseCase` instead of the whole `UserRepositoryInterface` (architecture-reviewer, slice 2). No test changed: the tests reach these controllers over HTTP; a mutation on the owner lookup fails 7 alert tests. No red, as for any move with unchanged tests. The two controllers and `accounts/wiring.py` joined the blocking mypy step. With this PR the accounts module plan is done |
| Characterization tests for billing | #196 | — | Before plans, subscriptions and plan limits move into a `billing` module. 9 e2e tests in `test_billing_characterization.py`: an inactive plan cannot be subscribed, subscribing switches the plan, the free plan cannot be canceled, canceling returns to Free, no plans → a synthesized Free (`plan_id` 0), `GET /plans/` leaves out inactive plans, a removed plan is 404 (not a neighbor), canceling records `canceled_at`, a pro user's limits keep 90 days of price history. 13 mutations: the first 5 tests killed 8, the 4 later ones kill the rest except M9 (subscription `updated_at` not written), accepted by the author (Nov 17, 2026) because nothing reads the field. Approved by the author (Nov 16 and 17, 2026). Unused, for a later Remove Dead Code: `PlanRepository.update`, `SubscriptionRepository.get_by_id` |
| Billing slice 1: `Plan` and `Subscription` are pure dataclasses | #199 | Primitive Obsession on a framework type → Move Class (to `billing/entities.py`) + Replace Pydantic model with dataclass | `Plan` and `Subscription` were Pydantic models in `src/app/entities/`; they are now `@dataclass(kw_only=True)` in `billing/entities.py` with the same fields and defaults (the subscription dates still default to now). The repositories map ORM rows field by field and write with `asdict`; the subscription update writes the same fields as before. `PlanRepository.update` (unused) now writes every field instead of the set ones; it goes away in slice 2. Test diff (the import in `test_plan_limit_rules.py`) approved by the author (Nov 17, 2026); red was a `ModuleNotFoundError`, as expected for a move. `billing/entities.py` joined the blocking mypy step |
| Billing slice 2: persistence | #200 | Move Class + Remove Dead Code | The plan and subscription ORM models → `billing/persistence/models.py`, their repositories → `billing/persistence/repositories.py`, the repository interfaces → `billing/ports.py` (the plan files moved with `git mv`, the subscription ones merged in), and every import updated (model registry, controllers, `interfaces/http/plan_limits.py`, `load_fixtures.py`). `PlanRepository.update` and `SubscriptionRepository.get_by_id` (never called) are removed with their interface methods. The subscription update writes `updated_at` through the same loop as the other fields, which clears its mypy error (whole backend 242 → 241). Test diff (imports in `e2e/conftest.py` and three e2e test files) approved by the author (Nov 17, 2026); red was a `ModuleNotFoundError`. The three files joined the blocking mypy step |
| Billing slice 3: use cases | #201 | Extract Function + Move Function | The logic written inside `plan_controller` and `subscription_controller` moves to `billing/use_cases.py`: `ListPlansUseCase`, `GetPlanUseCase`, `CreatePlanUseCase`, `GetMySubscriptionUseCase` (the synthesized Free takes `member_since`, not the user), `SubscribeUseCase` and `CancelSubscriptionUseCase`. They return entities or `MySubscription(subscription, plan_name)` and raise `PlanNotFoundError`, `PlanInactiveError`, `NoSubscriptionError` and `AlreadyFreeError`, which the controllers map to the same 404 and 400 errors as before; the subscribe and cancel log lines move with them. New unit tests with in-memory fakes for the ports (9, `tests/unit/billing/test_subscriptions.py`), scope approved by the author (Nov 17, 2026: only the use cases that decide something; list/get/create plans stay covered by e2e). Red on assertions from a skeleton returning empty values. `/subscriptions/me/limits` waits for slice 4. `billing/use_cases.py` joined the blocking mypy step |
| Billing slice 4a: a user's plan limits come from billing | #202 | Move Function + Extract Function | `PlanLimits`, `FREE_PLAN_DEFAULTS` and `limits_for_plan` move from `domain/plan_limits.py` to `billing/limits.py`; the new `GetUserPlanLimitsUseCase` answers "what are user X's limits?" (no subscription, or a subscription to a removed plan, gets the free defaults, as before). The FastAPI dependency in `interfaces/http/plan_limits.py` (used by `/subscriptions/me/limits`, alerts and saved searches) calls it. Slice 4 is split in two PRs because it touches two modules; 4b moves alerts' limit rules into alerts. Test diff approved by the author (Nov 17, 2026): 4 unit tests with the slice 3 fakes, and the `PlanLimits`/`limits_for_plan` imports in two domain tests. Red on assertions from a skeleton returning zeros. `billing/limits.py` joined the blocking mypy step |
| Billing slice 4b: alerts apply the plan limits themselves | #203 | Inappropriate Intimacy → Extract Interface (port owned by the client) + Move Function | Alerts ask for the limits through their own `AlertLimitsReader` port (`AlertLimits` dataclass; `BillingAlertLimits` adapter over billing's `GetUserPlanLimitsUseCase`, built by a new `billing/wiring.py`). `CheckAlertLimitsUseCase` applies the active-alert, frequency and store limits with today's messages and order, counting alerts with alerts' own repository; the update conditions written in the controller (reactivated, frequency changed, stores changed) move into `for_changes`. `interfaces/http/plan_limits.py` is gone: the limits dependency is `billing/http/limits.py`, alerts map a violation in `alerts/http/limits.py`, and saved searches keep their store and "run now" rules in `domain/plan_limits.py` with a local error mapping until they get a module (the store rule exists twice meanwhile). Test diff approved by the author (Nov 17, 2026): 13 unit tests in `tests/unit/alerts/test_alert_limits.py`; `test_plan_limits.py` (the removed `check_*` helpers) and the alert/frequency rule tests in `test_plan_limit_rules.py` removed. Red on assertions from a skeleton returning no violation. Playwright 32/32. Four new files joined the blocking mypy step |
| Billing slice 5: HTTP | #204 | Move Function | The plan and subscription schemas, presenters and controllers leave `interfaces/http/` for `billing/http/`. `billing/wiring.py` builds the repositories for them (typed as billing's ports), so nothing outside billing's persistence and wiring builds `PlanRepository` or `SubscriptionRepository`. The two collection responses get the same narrow `type: ignore[assignment]` as accounts' `UsersCollectionResponse` (whole-backend mypy 241 → 239). No test changed: the tests reach these controllers over HTTP; a mutation (inactive plan answered 404 instead of 400) fails a characterization test. No red, as for any move with unchanged tests. The two controllers joined the blocking mypy step. With this PR the billing module plan is done |
| Characterization tests for stores | #206 | — | Before source websites (stores) move into their own module. 11 e2e tests in `test_stores_characterization.py`: a regular user gets 403 on create, update and delete; a partial update keeps the fields left out (name, `base_url`, `is_active`) and moves `updated_at` forward; the list shows the newest store first, `sort_by` without `sort_order` sorts descending, an unknown `sort_by` falls back to newest first; deleting a store an alert or a saved search uses answers 204 and drops the link. 19 mutations: the existing suite killed 7, these tests 10 more; survivors accepted by the author (Nov 18, 2026): M11 (`updated_at` not set by the repository, equivalent because the model's `onupdate` sets it) and M19 (the 404 pointer of get-by-name). Approved by the author (Nov 18, 2026) |
| Stores slice 1: `Store` is a pure dataclass | #209 | Primitive Obsession on a framework type → Move Class (to `stores/entities.py`) + Replace Pydantic model with dataclass + Rename Class | `SourceWebsite` (Pydantic, `src/app/entities/`) becomes the `@dataclass(kw_only=True)` `Store` in the new `stores/entities.py`, same fields and defaults (the dates still default to now); the name `Store` inside the module was decided by the author (Nov 18, 2026), the HTTP contract and the table keep `source_website`. The repository creates with `asdict`, reads with `fields` and updates the fields it wrote before (`name`, `base_url`, `is_active`). The old file is removed and the imports repointed; the tests only changed the import and the class name. `stores/entities.py` joins the blocking mypy step |
| Stores slice 2: persistence | #210 | Move Class + Rename Class | The ORM model → `stores/persistence/models.py` as `Store` (table `source_websites` unchanged), the repository → `stores/persistence/repositories.py` as `StoreRepository`, its interface → `stores/ports.py` as `StoreRepositoryInterface`. The relationship strings in catalog, alerts and saved searches say `"Store"`; the package exports, the admin dashboard, the fixture scripts and the other modules' imports follow the new path. API error texts that say `SourceWebsite` are contract and stay. Tests: import and name only, plus `test_source_website_repository.py` → `test_store_repository.py`; one test the approved diff missed (`test_product_repository.py`, an import through the package) got the same change, approved by the author (Nov 18, 2026). The three files join the blocking mypy step (the old `updated_at` assignment error fixed) |
| Stores slice 3: use cases | #211 | Extract Function + Move Function + Introduce Parameter Object (`StoreChanges`) | `use_cases/source_website_use_cases.py` → `stores/use_cases.py`: create, get by id, get by name, list, update, delete. A missing store is a `StoreNotFoundError` instead of `None`/`False`; the partial-update merge leaves the controller for `UpdateStoreUseCase` (`StoreChanges`, None keeps the current value). The controller maps the error to the same 404s and still checks the store exists before validating an update body (today a missing store answers 404 even with an invalid body). Tests: 9 unit tests with an in-memory fake (`tests/unit/stores/test_use_cases.py`) replace the 13 mock-based pass-through tests, approved by the author (Nov 18, 2026); create and list stay covered by e2e. `stores/use_cases.py` joins the blocking mypy step |
| Stores slice 4: consumers | #212 | Inappropriate Intimacy → Extract Interface (port owned by the client) + adapter; Rename Parameter | Catalog's `offer_controller` asked `StoreRepository` directly; now it asks catalog's own `StoreDirectory` port (`exists`, `id_named`), implemented by `catalog/adapters/stores.py` over stores' use cases and built by `catalog/wiring.py`. The new `stores/wiring.py` gives other modules stores' use cases (`store_by_id`, `store_by_name`); alerts' `StoreReader` adapter (`SourceWebsiteStores` → `StoreReaderOverStores`) wraps `GetStoreUseCase` from it. Catalog's ports say `store_ids` (`search_by_term_and_sources`) and `store_id` (`list_by_staleness`, the collection queue), decided by the author (Nov 18, 2026); `OfferInput`/`Product.source_website_id` and alerts' and saved searches' `source_website_ids` stay, since they mirror the API and the table. Tests: one mock assertion changed its keyword (`source_website_ids` → `store_ids`), approved by the author (Nov 18, 2026); the 422/404 for unknown stores and the store name in alert e-mails stay covered by e2e. The new files join the blocking mypy step |
| Stores slice 5: HTTP | #213 | Move Function + Rename Class | `source_website_schema`, `source_website_presenter`, `source_website_validator` and `source_website_controller` leave `interfaces/http/` and `domain/validators/` for `stores/http/` (`store_schema.py`, `store_presenter.py`, `validators.py`, `store_controller.py`), with `Store*` class names; the controller gets the repository from `stores/wiring.py` (`stores`). URLs, the JSON:API type, bodies and error texts are unchanged; only the OpenAPI component names now say `Store*` (nothing generates code from them). Tests: the validator and presenter tests move to `tests/unit/stores/` and the controller e2e file is renamed `test_store_controller.py`; imports and class names only. The four files join the blocking mypy step. **Stores module done** |
| Store test fixtures renamed | #214 | Rename Variable | Proposed after the stores module and agreed by the author (Nov 18, 2026) as its own PR: the test fixtures `sample_source_website`, `sample_source_website_entity` and `sample_source_website_collection` become `sample_store`, `sample_store_entity` and `sample_store_collection` in 19 test files. Names only; no assertion changed |
| Characterization tests for saved searches | #215 | — | Before search configs and their runs move into their own module (chosen by the author, Nov 18, 2026). A mutation run (28 mutations over the search-config and execution-log controllers, use cases, repositories, validator, `manual_run_violation` and the stale-run rule) left 12 survivors; 8 e2e tests in `test_saved_searches_characterization.py` kill all 12: the list shows the newest config first; a regular user gets 403 listing another user's configs; a partial update keeps the fields left out (term, `is_active`, frequency, metadata, stores); "Run Now" on an own config with no alert answers 404, and with more stores than the plan allows 403 `PLAN_LIMIT_REACHED` (`max_sources`); `execution-status` says `idle` before any run and shows a failed run's `error_message`; a config's runs list the latest first |
| Saved searches module plan | #216 | — | Six slices, approved by the author (Nov 18, 2026): see *Saved searches module plan* below |
| Saved searches slice 1: `SavedSearch` and `SearchRun` are pure dataclasses | #217 | Primitive Obsession on a framework type → Move Class (to `searches/entities.py`) + Replace Pydantic model with dataclass + Rename Class + Move Function | `SearchConfig` and `SearchExecutionLog` (Pydantic, `src/app/entities/`) become the `@dataclass(kw_only=True)` `SavedSearch` and `SearchRun` in the new `searches/entities.py`, same fields and defaults; the run statuses and `is_stale_run` move there from `domain/search_runs.py`. `SearchRun` still refuses an unknown status (in `__post_init__`), so `POST /search-execution-logs/` with a bad status keeps answering 500 (checked before and after). The repositories already mapped fields one by one. The old files are removed and the imports repointed; the tests only changed the import and the class names. `searches/entities.py` joins the blocking mypy step |
| Saved searches slice 2: persistence | #218 | Move Class + Rename Class | The search config model, its store link table and the execution log model → `searches/persistence/models.py` (`SavedSearch`, `search_config_source_website`, `SearchRun`); both repositories → `searches/persistence/repositories.py` (`SavedSearchRepository`, `SearchRunRepository`), which now map fields generically like billing and stores; their interfaces → `searches/ports.py`. Tables unchanged; the relationship names in accounts, stores and alerts, the package exports, admin, dashboard, the fixtures script and the alembic comment follow. Tests: imports and class names only (one `assert` names the model). The three files join the blocking mypy step; whole-backend mypy 231 → 207 |
| Saved searches slice 3: use cases | #219 | Extract Function + Move Function + Introduce Parameter Object (`SavedSearchChanges`, `SearchRunChanges`) + Remove Dead Code | The search-config and execution-log use cases move to `searches/use_cases.py` (`CreateSavedSearchUseCase`, `GetSavedSearchUseCase`, `UpdateSavedSearchUseCase`, `DeleteSavedSearchUseCase`, `GetSearchRunUseCase`, `UpdateSearchRunUseCase`, `GetLatestSearchRunUseCase`…). The partial-update merge and the not-found checks leave the controllers: the use cases raise `SavedSearchNotFoundError` / `SearchRunNotFoundError`, mapped to the same 404s; the controller keeps the ownership check in one helper. `UpdateSearchRunUseCase` takes `now`. The unused `DeleteSearchExecutionLogUseCase` is removed, and with it the `src/app/use_cases/` folder. Tests: 20 use case tests over in-memory fakes in `tests/unit/searches/test_use_cases.py` replace the 2 mock-based files (decided by the author, Nov 18, 2026); the delete's "in use" check keeps its e2e coverage until slice 4. `searches/use_cases.py` joins the blocking mypy step |
| Saved searches slice 4: Run Now | #220 | Inappropriate Intimacy → Extract Interface (ports owned by the client) + adapters; Extract Function + Move Function | The trigger's rules leave `search_config_controller` for `RunSearchNowUseCase`, which raises `SavedSearchNotFoundError` (404), `RunLimitReachedError` (403) and `SearchAlreadyRunningError` (409). It reaches alerts, billing and the scrapers' queue through ports searches owns (`SearchAlerts`, `RunLimitsReader`, `SearchDispatcher` in `searches/ports.py`), with adapters in `searches/adapters/` built by `searches/wiring.py`; alerts exposes its repository port through `alerts/wiring.price_alerts`. The delete's "in use" check goes through `SearchAlerts` as well. `source_limit_violation` and `manual_run_violation` move from `domain/plan_limits.py` into `searches/entities.py` over a searches-owned `RunLimits`. Tests: 10 Run Now and 2 delete tests over fakes (shared in `tests/unit/searches/fakes.py`); the limit rule tests move with the rules, `limits_for_plan`'s to `tests/unit/billing/`; two e2e files patch the dispatcher at its new path. A mutation run over the new code killed 7 of 8; the survivor (the alerts adapter matching any of the user's alerts) was already uncovered before this PR |
| Saved searches slice 5: consumers | #229 | Inappropriate Intimacy → Extract Interface + adapter over use cases | Alerts' `SearchConfigKeywordSearches` takes searches' use cases (`CreateSavedSearchUseCase`, `GetSavedSearchUseCase`, new `FindSavedSearchByTermUseCase`, `UpdateSavedSearchUseCase`) built by `searches/wiring.py`, no longer the repository. The update sends only the fields alerts knows (`SavedSearchChanges`), so preferred time and metadata stay as they are; alerts never changes a search's owner, so `user_id` is not part of it. `searches.wiring` and `alerts.wiring` import each other (used only inside functions): revisit in slice 6. Only the adapter's fixture changed in the existing tests; 3 new unit tests for the new use case. Approved by the author (Nov 22, 2026) |
| Saved searches slice 6: HTTP | #230 | Move Function + Rename Class; Inappropriate Intimacy → Extract Interface + adapter | `search_config_schema`, `search_execution_log_schema`, their presenters, both validators and both controllers leave `interfaces/http/` and `domain/validators/` for `searches/http/` (`saved_search_schema.py`, `search_run_schema.py`, `saved_search_presenter.py`, `search_run_presenter.py`, `validators.py`, `saved_search_controller.py`, `search_run_controller.py`), with `SavedSearch*` and `SearchRun*` class names. The controllers get repositories and the validator from `searches/wiring.py`; the validator checks stores through searches' own `SearchStores.exists` port (adapter over stores' `GetStoreUseCase`) instead of stores' repository. URLs, JSON:API types, bodies and error texts are unchanged; only the OpenAPI component names change. Tests: validator and presenter tests move to `tests/unit/searches/`, the two controller e2e files are renamed; imports and class names only, plus the store mock in two validator tests (`get_by_id` → `exists`). Approved by the author (Nov 22, 2026). The new files join the blocking mypy step; whole-backend mypy 207 → 204. **Saved searches module done** |
| Unused dashboard summary removed | #261 | Dead Code → Remove Dead Code | `GET /dashboard/summary` (a user's alert counts, opportunities and next checks) had no client: the admin dropped its dashboard service in #98 and the site never called it. Found while scoping the admin module; removal decided by the author (Nov 28, 2026). The controller, its three e2e tests, the admin's unused endpoint constant and one status check in `test_price_alert_ownership.py` (approved by the author) go. `/admin/summary` and `/admin/cleanup-products` stay and get characterization tests next |
| Characterization tests for admin | #262 | — | Before the admin gets its own module. 15 e2e tests in `test_admin_characterization.py`. `GET /admin/summary`: a staff user gets 403; all users and the active ones; alert counts leave out soft-deleted alerts (active means active and not deleted); every product, available or not; all stores and the active ones; the latest 20 runs newest first, each as stored; scraper stats count successes and failures among those 20 (a running run counts only in the total). `POST /admin/cleanup-products`: keeps products newer than `days_old` (default 30) and the ones an active alert finds (term in the title, store among the alert's); a paused or soft-deleted alert keeps nothing; the alert's `max_price` plays no part. 22 mutations: the existing suite killed 1 (dry run deleting), these tests the other 21. Approved by the author (Nov 28, 2026) |
| Admin module plan | #263 | — | Three slices: see *Admin module plan* below |
| Admin slice 1: counts where the data lives | #264 | Extract Function + Move Function | Accounts, alerts, catalog and stores answer their own counts: `CountUsersUseCase`, `CountPriceAlertsUseCase` (soft-deleted alerts left out), `CountProductsUseCase` and `CountStoresUseCase`, each with `active_only` where the admin needs it, over a new `count()` on the module's repository port. Searches needs no new use case: `ListSearchRunsUseCase` sorted by `started_at` desc gives the latest runs (the plan's `ListLatestRunsUseCase` dropped). Tests: 7 integration tests over the real repositories on SQLite (`tests/integration/test_counts.py`), since the rules live in each query; approved by the author (Nov 28, 2026), with a fake count added to `FakeStores` and one model-registry import added before the red. Red on assertions (`assert 0 == 2`) from repositories that returned 0. mypy unchanged (203) |
| Admin slice 2: admin summary | #265 | Inappropriate Intimacy → Extract Interface (port owned by the client) + adapter; Move Function | The new `admin` module. `admin/entities.py`: `AdminSummary`, `Counts`, `RecentRun` and `ScraperStats.of` (successes and failures among the recent runs; another status counts only in the total). `admin/ports.py`: `PlatformStats`, implemented by `admin/adapters/platform_stats.py` over slice 1's count use cases and searches' `ListSearchRunsUseCase`, which each module's wiring now builds (`count_users`, `count_price_alerts`, `count_products`, `count_stores`, `list_search_runs`). `GetAdminSummaryUseCase` asks for the latest 20 runs; `admin/wiring.py` builds it. The controller moves to `admin/http/admin_controller.py` with a presenter that builds the same body; the cleanup endpoint moves with it unchanged until slice 3. Tests: 4 unit tests over a fake `PlatformStats` (`tests/unit/admin/test_admin_summary.py`), approved by the author (Nov 28, 2026); the body stays pinned by #262. Red on assertions from a skeleton returning a zero summary. The admin files except the controller join the blocking mypy step; whole-backend mypy 203 → 203 |

## Accounts module plan

Approved by the author (Nov 16, 2026). `accounts` holds users, sign-up,
login/tokens and the logged-in user; plans and subscriptions go to a
`billing` module later. One PR per slice, behavior unchanged:

1. **Entity** #189: `User` becomes a pure dataclass in
   `accounts/entities.py`; the e-mail format is checked only by the request
   schemas.
2. **Persistence** #190: the ORM model, the repository and its interface move to
   `accounts/persistence/` and `accounts/ports.py`.
3. **Use cases and validation** #191: `user_use_cases.py` to
   `accounts/use_cases.py`, `user_validator.py` to
   `accounts/http/validators.py`.
4. **Login and the logged-in user** #192: `security/auth.py` and token creation
   to `accounts/http/`; `create_access_token`'s unused default expiry is
   removed (Remove Dead Code).
5. **Controllers**, in two PRs: (5a) #193: the auth and user schemas and
   presenters to `accounts/http/`; (5b) #194: the auth and user controllers to
   `accounts/http/`, built by `accounts/wiring.py`. `admin_controller` is not
   accounts (it summarizes and cleans products, stores and alerts): it waits
   for the shared-infra step.

Other modules' http layers may depend on `accounts` (the logged-in user).

## Billing module plan

Approved by the author (Nov 17, 2026). `billing` holds plans, subscriptions
and plan limits; the characterization tests (#196) pin its behavior. One PR
per slice, behavior unchanged:

1. **Entities** #199: `Plan` and `Subscription` become pure dataclasses in
   `billing/entities.py`; the repositories map ORM rows field by field.
2. **Persistence** #200: the ORM models, the repositories and their interfaces
   move to `billing/persistence/` and `billing/ports.py`; the unused
   `PlanRepository.update` and `SubscriptionRepository.get_by_id` are removed
   (Remove Dead Code).
3. **Use cases** #201: the logic written inside the plan and subscription
   controllers (list, get and create plans; my subscription with the
   synthesized Free; subscribe; cancel; my limits) moves to
   `billing/use_cases.py`. They return plain data or a domain error; JSON:API
   stays at the edge.
4. **Plan limits**, in two PRs: (4a) #202: billing answers one question, "what are user X's
   limits?" (`PlanLimits`, `limits_for_plan` and a `GetUserPlanLimits` use
   case). The rules that compare a request with a limit (active alerts,
   minimum frequency, sources) move to `alerts`, which asks for the limits
   through its own port (adapter over billing) and counts its own alerts, so
   billing no longer imports alerts' `PriceAlertRepository`
   (decided by the author, Nov 17, 2026); (4b, this PR) the alerts side. `interfaces/http/plan_limits.py`
   goes away. `manual_run_violation` (saved searches' "run now") stays where
   it is, reading the limits from billing, until saved searches get a module.
5. **HTTP** #204: the plan and subscription schemas, presenters and controllers
   move to `billing/http/`, built by `billing/wiring.py`.

## Stores module plan

Approved by the author (Nov 18, 2026). `stores` holds the stores prices are
collected from (today "source websites"); the characterization tests (#206)
pin their behavior. Inside the module the code says `Store` (decided by the
author, Nov 18, 2026: the old name dates from before the comparator); the
HTTP contract stays as it is (`/source-websites/`, JSON:API type
`source_website`, the `source_websites` table), since the scrapers and the
admin use it. One PR per slice, behavior unchanged:

1. **Entity** #209: `SourceWebsite` (a Pydantic model) becomes the pure dataclass
   `Store` in `stores/entities.py`; the repository maps fields one by one
   instead of `model_dump` (Replace Pydantic model with dataclass + Rename
   Class).
2. **Persistence** #210: the ORM model, the repository and its interface move to
   `stores/persistence/` and `stores/ports.py` (Move Class); the other
   modules' imports of the ORM model follow the new path.
3. **Use cases** #211: the six pass-through use cases move to
   `stores/use_cases.py`; the partial-update merge and the "exists, or 404"
   checks leave the controller for the use cases, which return plain data or
   a domain error (Extract Function + Move Function).
4. **Consumers** #212: catalog's `offer_controller` (does the store exist, which
   id has this name) asks through a catalog-owned port with an adapter over
   stores; alerts' `StoreReader` adapter is built from `stores/wiring.py`
   (Inappropriate Intimacy → Extract Interface).
5. **HTTP** #213: the schema, presenter, validator and controller move to
   `stores/http/`, built by `stores/wiring.py` (Move Function).

Left for the queue: catalog's and alerts' persistence join the stores table
for the store name (persistence coupling, like catalog → alerts before #182);
the search-config validator only changes its import until saved searches get
a module; deleting a store that has offers answers 500.

## Saved searches module plan

Approved by the author (Nov 18, 2026). `searches` holds the
collector searches (today "search configs") and their runs (today "search
execution logs"); the characterization tests (#215) pin their behavior.
Inside the module the code says `SavedSearch` and `SearchRun`; the HTTP
contract stays as it is (`/search-configs/`, `/search-execution-logs/`, the
JSON:API types, the `search_configs`, `search_config_source_website` and
`search_execution_logs` tables), since the scrapers, the admin and the site
use it. One PR per slice, behavior unchanged:

1. **Entities** #217: `SearchConfig` and `SearchExecutionLog` (Pydantic models)
   become the pure dataclasses `SavedSearch` and `SearchRun` in
   `searches/entities.py`, with the run statuses and `is_stale_run` from
   `domain/search_runs.py`; the repositories map fields one by one (Replace
   Pydantic model with dataclass + Rename Class + Move Function).
2. **Persistence** #218: the three ORM models, both repositories and their
   interfaces move to `searches/persistence/` and `searches/ports.py` (Move
   Class + Rename Class); accounts', stores' and alerts' relationship names
   and the admin and dashboard imports follow.
3. **Use cases** #219: the pass-through use cases of both move to
   `searches/use_cases.py`; the partial-update merge and the "exists, or
   404" checks leave the controller (Extract Function + Move Function +
   Introduce Parameter Object, like `StoreChanges`).
4. **Run Now** #220: the trigger's rules leave the controller for a
   `RunSearchNowUseCase`. It asks through ports searches owns: which alerts
   use a search (adapter over alerts; also the delete's "in use" check, now
   on alerts' repository), the user's plan limits (adapter over billing) and
   the dispatch to the scrapers (adapter over `celery_client`).
   `source_limit_violation` and `manual_run_violation` move from
   `domain/plan_limits.py` into searches, which owns its limit rules like
   alerts does since #203 (Inappropriate Intimacy → Extract Interface +
   Move Function).
5. **Consumers** #229: alerts' `KeywordSearches` adapter is built over searches'
   use cases from `searches/wiring.py` instead of the old repository
   (Inappropriate Intimacy → adapter over use cases, like stores #212).
6. **HTTP** #230: the schemas, presenters, validators and controllers of both
   move to `searches/http/`, built by `searches/wiring.py`; the
   search-config validator checks stores through a searches-owned port
   instead of importing stores' (Move Function + Extract Interface).

Left for the queue: the admin and dashboard controllers query the run ORM
model directly (they move when admin gets its home); searches' persistence
joins the stores table through `search_config_source_website`; the 404/403
and non-JSON:API answers found by the characterization.

## Admin module plan

Approved by the author (Nov 28, 2026). `admin` holds what only
the back office asks for: the platform summary and the product cleanup.
Today `interfaces/http/controllers/admin_controller.py` queries the ORM
models of accounts, alerts, catalog, stores and searches itself. The
characterization tests (#262) pin both endpoints. The HTTP contract stays
(`GET /admin/summary`, `POST /admin/cleanup-products`, the bodies, the
superuser check), since the admin page and the scrapers' daily cleanup task
use it. One PR per slice, behavior unchanged:

1. **Counts where the data lives** #264: each module answers its own count
   through a new use case and a repository method. Accounts:
   `CountUsersUseCase` (all and active). Alerts: `CountAlertsUseCase` (all
   and active, soft-deleted left out). Catalog: `CountProductsUseCase`.
   Stores: `CountStoresUseCase` (all and active). Searches:
   `ListLatestRunsUseCase` (the latest N runs, newest first). Unit tests over
   the modules' in-memory fakes, tests first (Extract Function + Move
   Function, out of the controller).
2. **Admin summary** #265: the new `admin` module. `admin/entities.py` holds
   `AdminSummary`, `Counts`, `RecentRun` and the scraper stats rule
   (successes and failures among the recent runs). `admin/ports.py` holds
   one port, `PlatformStats`, implemented by `admin/adapters/` over the five
   use cases of slice 1. `GetAdminSummaryUseCase` gets unit tests over a
   fake. The endpoint moves to `admin/http/` (controller and presenter,
   same body), built by `admin/wiring.py` (Inappropriate Intimacy → Extract
   Interface (port owned by the client) + adapter; Move Function).
3. **Cleanup in catalog**: decided by the author (Nov 28, 2026), since
   catalog owns the products. `ListingScope.found_by_alerts` gets
   `active_only` (alerts' adapter adds `is_active`). The new
   `DeleteStaleProductsUseCase` (`days_old`, `dry_run`, `now`) deletes the
   products not updated since the cutoff that no active alert finds and
   returns the eligible and deleted counts. Admin reaches it through its own
   `ProductCleanup` port with an adapter. The endpoint moves to
   `admin/http/` and the old controller is removed (Feature Envy → Move
   Function; Extract Interface + adapter). The admin files join the blocking
   mypy step.

Left as they are (pinned by #262): the alert's `max_price` plays no part
in the cleanup; a running run counts in the scraper stats total only.

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
- Accounts: done in 5b, alerts reads an owner through accounts'
  `GetUserByIdUseCase` (architecture-reviewer, slice 2). Still open: `admin_controller`
  queries the accounts ORM model directly; move it behind an accounts use
  case when admin finds its home. Done in 5a: the validator's schema
  imports (architecture-reviewer, slice 3).
- Validator tests live in `tests/unit/domain/validators/` but the code is
  now http-layer.
- Checks that need a repository (unique URL, product exists) may belong in
  the use cases rather than in request validation.
- Accounts: gaps covered #188. Done #235: a deleted user's token
  answered 404 and a deactivated user 400; now 401 and 403 (approved by the
  author, Nov 22, 2026). Done #238: deleting a user who still has data
  (alerts, soft-deleted ones included, notification logs, a subscription or
  saved searches) answered 500, or left the saved searches without an owner;
  now 409 `USER_HAS_DATA` and the user is kept (rule decided by the author,
  Nov 24, 2026: refuse, the admin deactivates instead). Done #239: the
  admin page explains the 409 from its code (pt and en) and a bulk delete
  reports how many users were deleted and how many were not.
- Accounts (Nov 24, 2026): the 409 is the admin's rule only. A user-initiated
  "delete my account" (LGPD erasure, deleting the user's data with them) is
  a separate flow, not planned yet. A soft-deleted alert blocks the delete
  for good, since nothing purges it.
- Alerts: done #240 (merged as #243): a deactivated user no longer gets
  alert e-mails; the skipped notice is not logged, so a reactivated user
  hears about an offer collected again (decided by the author, Nov 25,
  2026).
- Stores: an update of a missing store answers 404 before the body is
  validated, so the controller looks the store up twice (once before the
  validator, once in `UpdateStoreUseCase`). Validating first would drop one
  lookup but answer 400/422 for a missing store with a bad body: a question
  for the author (found in slice 3, Nov 18, 2026).
- Stores: done #251 (merged as #252): deleting a store that has offers answered
  500 (the ORM set `products.source_website_id`, which is `NOT NULL`, to
  null); now 409 `STORE_HAS_OFFERS` and the store, its offers and its links
  to alerts and saved searches are kept (rule decided by the author, Nov 27,
  2026: refuse, any offer counts, available or not). A store with no offers
  is still deleted and removed from alerts and saved searches. Done #253
  (merged as #254): the admin's websites page explains the 409 from its
  code (pt and en) and a bulk delete reports how many websites were deleted
  and how many were not.
- Saved searches (found in the characterization, Nov 18, 2026): another user's
  config answers 404 on GET but 403 on `/search-configs/user/{id}`; the
  trigger and `execution-status` bodies and that 403 are not JSON:API errors
  or resources. Pinned as they are; questions for the author.
- Done #234: `POST /search-execution-logs/` never called the run validator, so a bad status or a missing search answered 500 (found in slice 1, Nov 18, 2026). It now answers 422 or 404; the request type is the singular `search_execution_log` the scraper sends (decided by the author, Nov 22, 2026, who approved the one-word change in the customer journey test).
- Saved searches (found in slice 2, Nov 18, 2026): `SavedSearchRepository.delete`
  also detaches soft-deleted alerts through alerts' ORM model (persistence
  coupling to alerts, like catalog → alerts before #182).
- Saved searches (slice 5, Nov 22, 2026): `searches/wiring.py` and `alerts/wiring.py` import each other (searches reaches alerts for Run Now and delete, alerts reaches searches for keyword searches). It works because each uses the other only inside functions; a composition root above both modules would remove the cycle.
- mypy: 271 errors in 44 files outside the blocking list (#153); add paths
  to the blocking step as each area is fixed.
