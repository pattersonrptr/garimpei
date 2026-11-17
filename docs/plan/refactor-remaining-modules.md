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
3. **Use cases**: the logic written inside the plan and subscription
   controllers (list, get and create plans; my subscription with the
   synthesized Free; subscribe; cancel; my limits) moves to
   `billing/use_cases.py`. They return plain data or a domain error; JSON:API
   stays at the edge.
4. **Plan limits**: billing answers one question, "what are user X's
   limits?" (`PlanLimits`, `limits_for_plan` and a `GetUserPlanLimits` use
   case). The rules that compare a request with a limit (active alerts,
   minimum frequency, sources) move to `alerts`, which asks for the limits
   through its own port (adapter over billing) and counts its own alerts, so
   billing no longer imports alerts' `PriceAlertRepository`
   (decided by the author, Nov 17, 2026). `interfaces/http/plan_limits.py`
   goes away. `manual_run_violation` (saved searches' "run now") stays where
   it is, reading the limits from billing, until saved searches get a module.
5. **HTTP**: the plan and subscription schemas, presenters and controllers
   move to `billing/http/`, built by `billing/wiring.py`.

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
- Accounts: gaps covered #188. Questions for the author, each a fix
  with tests first: a deleted user's token answers 404 and a deactivated
  user 400 (401 and 403 would fit better); an admin cannot delete a user who
  owns an alert (the API answers 500).
- mypy: 271 errors in 44 files outside the blocking list (#153); add paths
  to the blocking step as each area is fixed.
