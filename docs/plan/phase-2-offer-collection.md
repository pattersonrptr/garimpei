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

## Decisions needed from the author

1. **Where does it run?** History only accumulates while a stack is up daily.
   Today nothing runs on the VPS. Options: deploy the Docker Compose stack to the
   VPS now (then 2e starts the clock), or build 2a-2d locally and deploy before 2e.
2. **Second source.** Candidates:
   - *Mercado Livre scraper*: exists, April notes say it works slowly, but it was
     empty on Nov 3 and is paused. Needs a spike to see what changed.
   - *Amazon*: best source of the **new** price, but scraping while being an
     Associate may cost the affiliate account (plan, section 8).
   - *Magalu*: unknown until the affiliate sign-up shows what data it gives.
3. **Where does the new-price anchor come from?** (Open decision in the plan.) If
   Estante Virtual's `novo` price is enough for the MVP, slice 2d can focus on
   more used offers.
4. **Seed list.** Which books, and how many to start (suggestion: 50 you care
   about, to see real history quickly).
5. **Scraping at a public scale.** The plan prefers feeds and APIs where they
   exist and showing only price and link (no copied photos or descriptions).
   Confirm that is the rule for these collectors.

## Spikes before the collectors (hours, not days)

- Does the Estante Virtual search accept an ISBN and return the book directly?
- Does the Radware challenge still pass from the container the scrapers run in?
- What changed on Mercado Livre between April and Nov 3?
