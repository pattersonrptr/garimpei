# Phase 4: price verdict and book alerts (plan)

Draft, Nov 2026. Goal from the main plan: **a "good price / wait" verdict and
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
| 4b | **Verdict on the book page** (done).  Badge and 90-day range bar at the top, server-rendered | A visitor sees whether to buy now, with no client JavaScript |
| 4c | **Book alerts.** `PriceAlert` targets a book and a condition; ingesting an offer evaluates that book's alerts | An offer under an alert's price sends the e-mail |
| 4d | **"Warn me".** Button on the book page opens the logged-in app with book, condition and suggested price filled in | A visitor creates a book alert in two steps after login |
| 4e | **Close.** Main plan updated; launch checklist listed | Phase 4 marked done |

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

## Expected

- With history from Nov 9-10, the first verdicts show around **Nov 24, 2026**.
  Until then the page says "learning". That is not a bug.

## Known limits (MVP)

- Notifications are deduplicated per alert and offer (as today): if the same
  offer drops further, no second e-mail.
