# Phase 4: price verdict and book alerts

**Done Nov 11, 2026** (#85-#88). Planned the same day. Goal from the main plan: **a "good price / wait" verdict and
a "warn me" button that creates an alert on the book. MVP ready to launch.**

## What exists

- Phase 2 collects new and used prices every day; `price_history` started on
  Nov 9-10, 2026.
- Phase 3 public pages: the book page leaves its top for the verdict and the
  90-day position bar. The API already returns daily lows per condition.
- Alerts are keyword alerts (`PriceAlert.search_term`), created in the Vite
  app (login). The book collector (`IngestOfferUseCase`) does not evaluate
  alerts.

## Slices (in order, one PR each)

| # | Slice | Done when |
|---|---|---|
| 4a | **Verdict in the catalog** (done, #85).  Pure rule (`catalog/verdict.py`), `JudgeBookPricesUseCase`, `verdicts` on `GET /books/{isbn}` | The book API says good / normal / high / learning per condition |
| 4b | **Verdict on the book page** (done, #86).  Badge and 90-day range bar at the top, server-rendered | A visitor sees whether to buy now, with no client JavaScript |
| 4c | **Book alerts** (done, #87). `PriceAlert` targets a book and a condition; ingesting an offer evaluates that book's alerts | An offer under an alert's price sends the e-mail |
| 4d | **"Warn me"** (done). Button on the book page opens the logged-in app with book, condition and suggested price filled in | A visitor creates a book alert in two steps after login |
| 4e | **Close** (done). Main plan updated; Phase 5 defined | Phase 4 marked done |

## Decisions (Nov 11, 2026)

1. **Verdict rule.** Per condition (new and used apart), over the daily lows of
   the last 90 days:
   - drop outliers with Tukey's fences (outside Q1 - 1.5 IQR, Q3 + 1.5 IQR;
     only with 4+ days). A store once listed a "new" copy at R$ 750;
   - fewer than **14 days** left: **learning** ("still learning this book's
     price");
   - lowest price in stock now <= 25th percentile: **good**; >= 75th: **high**
     (wait); in between: **normal**;
   - nothing in stock in that condition: **no_offer**.
   Percentiles use linear interpolation (`statistics.quantiles`, inclusive).
   The window includes today's low.
2. **"Warn me" goes to the logged-in app (Vite).** Login in Next.js waits for
   Phase 5. The link carries ISBN, condition and suggested price.
3. **A book alert is book + condition (new, used or any) + max price**, any
   store. The suggested price is the 25th percentile when there is history.
4. The verdict is part of `GET /books/{isbn}` so the page makes one request.
5. **Book alerts never get a SearchConfig.** A SearchConfig makes the old
   keyword scrapers search its term; a book alert must not send them looking
   for the book's title. The book's offers come from the collectors.
6. **A book alert is checked when an offer for the book comes in** (`POST
   /offers`, right after ingestion; a failure there is logged and never
   loses the price point) and when the alert is created or changed. Its
   frequency is always a day (books are collected daily), so the plan's
   frequency limit never blocks it.
7. **Wiring:** `offer_controller` (the composition root for ingestion) calls
   the alerts use case, as `product_controller` already does for keyword
   alerts. The planned `OfferIngestedListener` port was left out: one caller,
   no second implementation in sight.
8. Creating a book alert: `POST /price-alerts/` with `isbn` (10 or 13) and
   `condition` instead of `search_term`. 404 `BOOK_NOT_FOUND` when the book
   is not in the catalog; 409 `DUPLICATE_BOOK_ALERT` for a second alert on
   the same book and condition.
9. **"Warn me" link:** each offer column on the book page links to the
   logged-in app at `APP_URL/alertas/novo?isbn=…&condicao=usado|novo&preco=…`
   (no button when `APP_URL` is not set). Suggested price, in whole reais:
   the 25th percentile once there is a verdict, 10 % under today's lowest
   while learning, none when nothing is known.
10. **Coming back after login:** a protected page sends visitors to
    `/login?next=<path>`; login and sign-up keep `next` and return there.
    Only in-app paths are accepted (no `//host`, no absolute URLs), so the
    link cannot send anyone to another site.

## Expected

- With history from Nov 9-10, the first verdicts show around **Nov 24, 2026**.
  Until then the page says "learning". That is not a bug.

## Known limits (MVP)

- Notifications are deduplicated per alert and offer (as today): if the same
  offer drops further, no second e-mail.

## After 4d: what changed for Phase 5 (Nov 11, 2026)

Trying "warn me" in the browser showed the jump into the old Vite app (other
look, screens made for keyword alerts). Decided with the author:

- Phase 5 starts with the **user area in Next.js**: sign in / sign up, "My
  alerts", account. "My alerts" shows today's price against the target
  (link to the product page), the verdict badge and the notification history.
- The Vite app becomes **admin-only**. Dashboard and Products leave the
  user's view; admin keeps users (no "create user"), stores, search configs,
  scraper status and Flower.
- **Keyword alerts leave the user's screens.** Every alert targets a
  product. For categories without a code, a keyword may come back as a way
  to match offers to a product, not as a kind of alert.
- Books are the first category, not the product: names and screens stay
  generic.
- No commercial launch yet: the goal is a Garimpei that works for the author
  and could work for other users.

Open checklist before other people use it (not scheduled): hosting (AWS
track), affiliate links on offers, password reset, the e-mail sender on a
real domain, rate limiting on the public API.
