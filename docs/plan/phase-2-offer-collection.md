# Phase 2: offer collection (plan)

Draft, Nov 2026. Goal from the main plan: a seed list of books gets **daily
prices from at least 2 stores, new and used**, matched to books by ISBN, so
**price history starts accumulating**.

## What exists today

- Scrapers search by **keyword** for a user's alert, then scrape each product
  page and push it to the backend (`product`, `price_history`).
- `EstanteVirtualScraper` already reads both the `novo` and `usado` prices from
  a book page, but keeps one price and writes `condition` as "not found".
- OLX and Mercado Livre are **paused** (Nov 3: nothing found in local tests).
  The Mercado Livre notes from April say a slow, rate-limited run worked.
- The backend can create a book from an ISBN (Phase 1b) and an offer
  (`Product`) can point to it (`canonical_product_id`). Nothing sets that link
  yet.

## Slices (in order, each one small and shippable)

| # | Slice | Done when |
|---|---|---|
| 2a | **Ingest contract.** A staff/service endpoint takes a plain offer DTO (isbn, store, url, price, condition, availability), finds or creates the book, upserts the offer by URL, adds a price-history point | Posting the same offer twice updates it, adds history, creates no duplicate; tested at use-case level |
| 2b | **Seed list.** A list of ISBNs the system keeps fresh (a file in the repo to start) | One command loads it into the catalog |
| 2c | **Collector 1: Estante Virtual by ISBN**, new and used as separate offers | A seed book yields 1 new and/or used offers in the DB |
| 2d | **Collector 2** (source to decide, see below) | Same, from a second store |
| 2e | **Schedule.** A daily job runs the collectors over the seed list, stalest first | History grows by a point per offer per day without anyone clicking |
| 2f | **Freshness.** Each offer records when it was last checked | The API can say "updated 3 h ago" |

2a first: it is the contract every collector depends on, and it has no scraping
risk. Collectors only send plain DTOs; none writes to the database
(architecture rule 5).

## Decisions (Nov 2026)

1. **Where it runs:** the author's Windows PC, which is on every day. Docker
   Desktop in the background with CPU and memory limits, one Playwright browser
   at a time, so games are not affected. A day with the PC off just misses that
   day's point; the next run starts with the stalest books. AWS comes later as
   its own track (main plan, track A).
2. **New-price anchor:** Estante Virtual's `novo` price for now. Revisit when
   there is a better source.
3. **Second source:** not decided. Mercado Livre and Amazon are on hold. **No
   scraper is touched without talking to the author first.**
4. **Seed list:** the 50 best-selling books of all time, each ISBN validated
   against BrasilAPI (title must match). Grows later.
5. **Scraping rule:** store only price, link, condition, availability, store and
   seller city. Title, authors and cover come from book metadata (BrasilAPI), not
   from stores. Slow pace, one page at a time.
6. **Affiliate accounts:** none yet, and not needed until the public pages are
   live (Phases 3 and 4).

## Spikes before the collectors (hours, not days)

- Does the Estante Virtual search accept an ISBN and return the book directly?
- Does the Radware challenge still pass from the container the scrapers run in?
- What changed on Mercado Livre between April and Nov 3?
