# Garimpei: price comparator plan

> Living document. It records the decisions made in planning (Nov 2026) so
> later sessions read this file instead of rebuilding the conversation.
> Each phase is planned in detail (plan mode) only when it starts.

## 1. Goal

Add a **book price comparator** to Garimpei, in the spirit of Zoom and
Buscapé: search a book, see new and used offers side by side, know whether
the price is good right now. Start with books, grow into a general comparator.

The existing alert system **stays**. It becomes the retention feature
("tell me when it drops below R$ X"), not the way in.

## 2. Product decisions

| Topic | Decision |
|---|---|
| Change or addition | **Addition.** Comparator is the way in; alerts keep users coming back |
| First category | **Books** (ISBN makes matching nearly trivial). Generic model so other categories fit later |
| New or used | **Both.** The new price is the anchor; the used offers are the differentiator ("used from R$ 38, 57% less") |
| Audience | Everyone. **Books are only the first category**: a general comparator later, so names and screens stay generic (product, not book; user, not reader) |
| Features by priority | 1. Price verdict · 2. Shopping list · 3. ISBN barcode scan · 4. Wishlist import (Skoob/Goodreads) |
| Platform | **Mobile-first web**, installable as a PWA |
| Accounts | **Public** search and book pages; login only for alerts and lists |
| Name | **Garimpei** |
| Visual tone | Undecided: chosen in Phase 0 from a reference board |
| Monetization | **Affiliate links** on offers + current **freemium** plans (alerts only). Search is always free |
| Front-end | Migrate to a **single Next.js app** (SSR for SEO), incrementally |
| Data sources | Not tied to the existing scrapers. Use **whatever is most viable** to get results fast |

## 3. Constraints and scope guardrails

- **~5 h/week**, with AI doing most of the coding, and a **token budget**
  shared with other work: phases are small, sessions are short, and this file
  is the shared memory between sessions.
- **No deadline. Launch when it is usable.** First goal: functional for the
  author, built so other users can use it. Selling it comes only when it is
  ready (decided Nov 11, 2026). Anything that makes the MVP
  bigger must be flagged. If a phase grows past ~4 weeks of work, split it.
- **Sequence, not parallel.** Data first, screens later: the price verdict
  needs history, and history needs time, so collection starts before the UI.
- **Next.js without a big-bang migration.** The Next.js app starts with the
  new public pages only. The current logged-in area (Vite) keeps running and
  moves over later (Phase 5).

### Deliberately out of the MVP

Shopping list (needs shipping cost per store, which is hard to get), ISBN scan,
wishlist import, categories other than books, push/WhatsApp notifications,
mobile app. (Migrating the logged-in area is Phase 5, right after the MVP.)

## 4. Architecture rules

Based on the author's notes on *Clean Architecture* (Obsidian vault,
`Zettelkasten/03 - References/20260305184502 - Arquitetura Limpa - Robert C. Martin.md`).

1. **Dependency rule.** Source code arrows point inward. Entities know
   nothing about FastAPI, SQLAlchemy, Celery, Next.js or any store.
2. **The interface lives with its client.** The catalog use cases define the
   gateways they need (`BookMetadataGateway`, `OfferSource`). BrasilAPI, an
   affiliate feed or a scraper are plugins behind them. Test for every method:
   *does the consumer need it, or does the provider offer it?*
3. **Screaming architecture.** The backend is organized by domain
   (`catalog`, `alerts`, `accounts`, `billing`…), not by technical layer
   (`entities/`, `use_cases/`, `infrastructure/`). The comparator is born as
   the `catalog` module. Existing code is **refactored into domain modules
   incrementally**: one module per small PR, behavior unchanged, protected by
   the existing tests (see Phase 1).
9. **Pure entities.** Domain entities are plain dataclasses, with no
   Pydantic, SQLAlchemy or framework imports. Pydantic stays at the edges
   (HTTP schemas, settings). Existing Pydantic entities are converted when
   their module is refactored.
4. **Matching is a strategy per category.** `IsbnMatcher` first; another
   category means adding a matcher, not changing the core (OCP).
5. **Simple data across boundaries.** Collectors (scrapers, feed importers)
   send plain offer DTOs to the backend API, as scrapers do today. No
   collector writes to the database.
6. **Main is the composition root.** Wiring of concrete gateways happens in
   one place per entry point (API, worker, tests).
7. **Partial boundaries are fine.** Pay for a full boundary only where the
   axes of change really differ (for example, each data source).
8. **Tests are the outermost circle.** Rules (matching, verdict) are tested
   through use cases, not through the UI. E2E covers user journeys only.

## 5. Domain model (sketch; detailed in Phase 1)

```text
CanonicalProduct ──1:N── ProductIdentifier   (isbn13, ean, asin, mlb_id…)
       │                    category-specific attributes (author, publisher, edition…)
       └──1:N── Offer ──1:N── PriceHistory
                 ├── store (SourceWebsite)
                 ├── url, affiliate_url
                 ├── condition (new | used | …), is_available
                 └── source_kind (scrape | api | feed)

PriceAlert (exists) ──> can target a CanonicalProduct, not just a keyword
PriceVerdict (derived) = f(current lowest price, history window)
```

Migration must keep current alerts and products working. Today's `Product`
is effectively an `Offer` without a canonical product.

## 6. Phases

Each phase ends with something usable or observable.

| # | Phase | Delivers | Done when |
|---|---|---|---|
| 0 | **Visual direction** (done) | Reference board (Zoom, Buscapé, Google Shopping, Keepa, Estante Virtual, plus the author's prints) and three style directions | One direction chosen; basic tokens (colors, type, spacing) written down |
| 1a | **Screaming layout** (done) | Target folder layout decided; first module moved (the one `catalog` depends on: today's products/offers), dataclass entities | Layout recorded as a decision; moved module has pure entities; all tests pass with no behavior change |
| 1b | **Catalog model** (done, see `docs/architecture/catalog-model.md`) | `catalog` module: CanonicalProduct, ProductIdentifier, Offer, ISBN metadata via BrasilAPI, migration compatible with alerts | Given an ISBN, the backend creates or reuses a book with metadata; existing tests pass |
| — | **Refactor remaining modules** | `alerts`, `accounts`, `billing`… moved one by one, between other phases | Old layer folders are gone |
| 2 | **Offer collection** (done) | Most viable sources feeding offers (new + used), matched to books by ISBN, on a schedule | A seed list of books gets daily prices from at least 2 stores, new and used. **History starts accumulating** |
| 3 | **Public pages (Next.js)** (done, see `phase-3-public-pages.md`) | Search, book page with offers side by side, price chart, affiliate links | A visitor finds a book and goes to a store without logging in; pages render on the server |
| 4 | **Verdict + alerts** (done, see `phase-4-verdict-alerts.md`) | "Good price / wait" verdict; "warn me" button creates an alert on the book | **MVP usable** |
| A | **AWS track** (study, runs alongside) | Design how the stack runs on AWS (e.g. Celery broker on SQS, maybe SNS, managed Postgres, scheduled container tasks) and move pieces over in small, cost-capped steps | Planned in its own session before any resource is created; every step has a teardown |
| 5 | **User area in Next.js** (next; plan in plan mode) | Sign in / sign up, "My alerts" (today's price vs target with a link to the product page, the verdict, notification history; pause, change price, delete), account. The Vite app becomes **admin-only** (non-admins are sent to the Next.js area; no "create user" in admin). Keyword alerts leave the user's screens (backend keeps them); Dashboard and Products leave the user's view | A user never sees the Vite app; everything a user does has the Garimpei look |
| 6+ | **Later** | Plans and billing screens, shopping list, ISBN scan, wishlist import, more categories (a keyword may come back as a way to match offers to a product without a code, never as an alert type) | Prioritized when Phase 5 is done |

Phases 1 and 2 have no visible UI. That is deliberate: history has to start
accumulating before there is anything to show.

## 7. Data sources (research, Nov 2026)

Details and links are in the planning conversation; summary:

| Source | Data | Monetization | Starting point |
|---|---|---|---|
| BrasilAPI `/isbn` (CBL, Mercado Editorial, Open Library, Google Books) | Book metadata, free | — | Phase 1 |
| Estante Virtual | Scraper (no program or API found) | Maybe via Magalu affiliates (owner since 2020) — **check** | Phase 2 |
| Mercado Livre | Scraper; public search API returns 403 to common apps | Affiliates (needs a public content profile) | Phase 2 |
| Amazon | Creators API only after 10 sales in 30 days | Associates, 10 % on books, link with `tag` | Links from day 1; data source **open** |
| Magalu | Unknown | Affiliate program | Check after sign-up |
| Shopee | Affiliate Open Platform API after approval | Affiliates | After approval |
| Awin / Lomadee | Feeds / API (Lomadee: 10 req/min) | Networks | Later, for more stores |
| OLX, Enjoei | Scraper only (no read API, no program found) | None | Later |

Sign-ups the author does in parallel: Magalu, ML Afiliados, Amazon
Associados, Shopee, Awin.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Stale prices destroy trust | Always show "updated X hours ago"; refresh by priority |
| Wrong match is worse than no match | ISBN only in the MVP; review queue for doubtful matches |
| Terms of use when scraping at public scale | Prefer feeds/APIs where they exist; show only price and link (no copied photos or descriptions) |
| No source for the new price (anchor) | Phase 2 spike: Amazon terms, Magalu, publisher list price from metadata. A very slow, human-paced Amazon scraper is technically plausible (same approach as the ML scraper), but the risk is contractual: scraping while being an Associate may cost the affiliate account. Weigh both |
| Refactor stalls feature work | One module per small PR, behavior unchanged, interleaved with phases; never a big-bang rewrite |
| Scope creep with 5 h/week | Section 3 guardrails; flag anything that grows the MVP |
| Two front-ends for a while | Phase 5 has a fixed end: Vite is retired |

## 9. Open decisions

Each one becomes a short decision record when it is made.

- [x] Visual direction: verdict first, used highlight, gold palette (decided Nov 2026, see [visual-direction.md](visual-direction.md))
- [x] Entities are pure dataclasses; Pydantic only at the edges (decided Nov 2026)
- [x] Backend is refactored to a screaming, domain-first layout, incrementally (decided Nov 2026)
- [x] Module list and folder layout: one module per domain, `catalog` first (decided Nov 2026; record in `docs/architecture/screaming-layout.md` on branch `refactor/screaming-layout`)
- [x] How `catalog` relates to today's `Product`: `Product` stays as the offer (renamed later); a nullable `canonical_product_id` links it to a `CanonicalProduct` (decided Nov 2026, see `docs/architecture/catalog-model.md`)
- [ ] Source of the new-book price anchor (Phase 2)
- [x] Verdict rule: 90 days, outliers out (Tukey), 14 days minimum, good <= P25, high >= P75 (decided Nov 2026, see [phase-4-verdict-alerts.md](phase-4-verdict-alerts.md))
- [x] Where daily collection runs: the author's Windows PC (Docker Desktop, in the background, resource-capped) until the AWS track is ready (decided Nov 2026). The VPS is not a target; it belongs to another project
- [ ] AWS design (track A): broker (SQS?), notifications (SNS?), database, scheduling, cost guardrails. Note: an AWS Budget alerts, it does not stop charges
- [ ] Hosting for Next.js (Phase 3; AWS track)
