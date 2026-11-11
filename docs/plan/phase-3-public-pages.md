# Phase 3: public pages (plan)

Draft, Nov 2026. Goal from the main plan: **a visitor finds a book and goes to
a store without logging in; pages render on the server.**

## What exists

- Phase 2 collects new and used prices for 50 books from 3 stores every day
  (`price_history` grows by a point per offer per day) and every offer knows
  when it was last checked.
- Every catalog endpoint needs a login: there is no public read API.
- The only UI is the Vite app (logged-in area). The main plan says the
  Next.js app starts with the new public pages only (no big-bang migration).

## Slices (in order, one PR each)

| # | Slice | Done when |
|---|---|---|
| 3a | **Public book API.** `GET /books?q=`, `GET /books/{isbn}`, `GET /books/{isbn}/price-history`, no login | A client can search, open a book with its offers and get its daily lows without a token |
| 3b | **Next.js app** (`web/`): layout with the Phase 0 tokens, home with search, results page, Docker Compose service, CI job | `docker compose up` serves the search on port 3000, rendered on the server |
| 3c | **Book page.** Savings block (used vs new), used and new columns, "updated X h ago", links to the stores, a "see on Amazon" link built from the ISBN | A visitor goes from search to a store in two clicks |
| 3d | **Price chart and SEO.** 90-day chart of the daily lows (server-rendered SVG), page metadata, `sitemap.xml` | The chart shows on the book page with no client JavaScript; search engines get a title, description and sitemap |

The verdict ("buy now / wait") and the 90-day position bar are Phase 4. The
book page leaves their place at the top.

## Decisions (Nov 2026, taken while the author was away; revisit freely)

1. **Read model in the `catalog` module.** The public pages need a different
   shape than the offer CRUD (a book with its offers, lowest new and used,
   daily lows), so the catalog gets a `BookCatalogReader` port and three small
   use cases, not new methods on the offer repository (rule 2: the interface
   belongs to its client).
2. **Only offers matched to a book are public.** Keyword-alert listings (no
   `canonical_product_id`) never show on the public pages.
3. **Store names are presentation.** The API returns the store slug
   (`estante_virtual`); the web app maps it to "Estante Virtual".
4. **Lowest prices count only offers in stock.** An out-of-stock offer is
   still listed (with its last price), but never as "from R$ X".
5. **Daily lows:** the price history endpoint returns, per day and condition,
   the lowest price seen that day (days in Brazil's time zone). That is what
   the chart and, later, the verdict need, and it hides how many offers or
   checks there were.
6. **Affiliate links:** no affiliate accounts yet (Phase 2, decision 6).
   Offers link to the store page as is. The Amazon link is a search by ISBN
   with an optional associate tag from the environment, so it earns from day
   one once the tag exists (Phase 2, decision 8: Amazon is never scraped).
7. **Next.js:** App Router, TypeScript, server components fetch the backend
   from the server. Plain CSS with the Phase 0 tokens as CSS variables, no UI
   kit: the public pages are few, and a small bundle matters for mobile-first.
   The chart is an SVG drawn on the server, no chart library.
8. **Light theme only** for now (Phase 0 left dark open). Revisit after launch.
9. **Hosting:** local Docker Compose until the AWS track decides (main plan,
   open decision).
10. **Public API safety:** read-only, no personal data, page size capped at
    50. Rate limiting waits until there is a public deployment.
