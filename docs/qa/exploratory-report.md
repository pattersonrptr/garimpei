# Exploratory test report — customer journey

**Date:** 2026-11-03 · **Build:** local Docker Compose stack · **Branch with fixes:** `fix/customer-journey`

## How it was tested

The app was used the way a real customer would use it, with three profiles:

- a **visitor** (not signed in);
- a **customer** on the Free plan;
- an **administrator**.

Every GET endpoint of the API (35) was also called with each profile.

Security held up:

- visitors get no private data;
- customers never see other users' data;
- signing up cannot grant admin rights.

The problems were about **product value**. A customer could not tell whether a search worked, why the plan blocked an action, or what they gained from an alert.

Each finding below became a **user story** in Playwright (`frontend/e2e/stories/`). The letter in a test's title points to this table. Rules that are cheaper to check below the UI also got backend tests (`backend/src/tests/e2e/test_customer_journey.py`).

## Findings

| # | Problem found | How the customer felt it | Status |
|---|---|---|---|
| A | Deleting a search config returned a 500 error. | "Could not delete." | ✅ A search still used by alerts answers **409** with "used by N alert(s)", which the admin page shows. Searches whose only alerts were deleted can be removed, together with their run history. |
| B | "Run now" never finished. The run log stayed *running* forever, each batch opened a new log and released the lock early, and runs that found nothing never closed. | The rocket spins and nothing happens. | ✅ A run is now **one log**, updated as it goes (`listings_found`, `listings_checked`). The UI shows progress ("checking 5 of 12 listings"), also when the page is opened mid-run, and a summary at the end. A run lost for 35 min is closed as failed instead of blocking new runs. Known listings are re-priced too. |
| C | Raising an alert's max price did not re-check listings already collected. | "I set 500 and it found nothing." | ✅ Creating or editing an alert evaluates the collected listings and emails each opportunity once. |
| D | The max price field had no explanation. | Didn't know what the field filters. | ✅ Every field in the alert form has helper text. |
| E | The Products page listed what *everyone* searched for. | A polluted list. | ✅ Customers see the listings their alerts found. Staff keep the whole catalog, and edit/delete is shown only to staff (the API already refused it). |
| F | The title filter did nothing. | "Search doesn't work." | ✅ Title, condition and availability filters reach the API. Title matching ignores case and accents. There is also a new **Opportunities only** filter. |
| G | "Select all" did not enable bulk delete (Products, Users, Search configs, Source websites). | Can't delete many at once. | ✅ DataGrid 8 reports "select all" as an *exclude* model; it now resolves to the rows on screen. |
| H | Admins saw every customer's alerts under "My alerts". | — | ✅ "My alerts" is always your own. Staff tools ask for `scope=all`. |
| I | The dashboard said "create alerts to start" to people who already had alerts, and showed little value. | Looks like nothing happened. | ✅ Onboarding only for new users. Opportunities link to the listing and show how much you save. |
| J | Pausing an alert also blocked "Run now". | "I thought pause was only for the schedule." | ✅ Paused alerts can still be run by hand. |
| K | The "Source websites" field had no accessible name. | A screen reader says only "combobox". | ✅ Labelled. Icon buttons got labels too. |
| L | Plan limits showed as "Could not create the alert", with no reason. | "Why didn't it let me?" | ✅ The form shows the plan's minimum frequency and site limit up front. A refusal explains the limit, in the user's language, with a link to the plans. |
| M | Sites showed as `estante_virtual`, and the list offered OLX and Mercado Livre, which returned nothing. | Looks unfinished. | ✅ Brand names are shown. OLX and Mercado Livre are paused (migration) until their scrapers are fixed. |
| N | The marketplace returns loosely related results, and all of them were saved. | Junk in the list. | ✅ Only listings whose title contains the search term are saved. |
| O | A mistyped address showed the landing page. | — | ✅ A real "page not found" page. |
| P | Admins see a search's frequency in **days**; customers see an alert's in **minutes**. | Confuses searches and alerts. | ⏸ Open. Needs a product decision: hide search configs from the admin menu, or rename the fields. |
| Q | The product page didn't say which alert found it or how much you save, and the description was one huge block. | Can't see the value. | ✅ A "Your alerts" section shows each matching alert and the savings. Long descriptions collapse. |
| R | "Last check" stayed "Never" after "Run now". | — | ✅ Fixed by B: the run log is closed with its finish time. |
| S | Visitors get 403 instead of 401, and a wrong password gets 400. | Only affects API integrators. | ⏸ Open. Low impact; changing it touches every client. |
| T | Plan limits could be bypassed by **editing** an alert (lower frequency, more sites, reactivating a 4th one). Found while fixing L. | — | ✅ Editing applies the same plan checks as creating. |
| U | Deleting a listing that had already triggered an email returned a 500 error (foreign key on `notification_logs`). Found by story C's cleanup. | Admin can't delete the listing. | ✅ The email history is kept, without the listing. |
| V | Batches queued by the old code keep running after an update: 40 batches (~200 s each) sat ahead of a new "Run now", and they save listings without the term filter (N). Found during the live run. | "Run now" seems stuck for an hour. | ⚠️ Cleared from the local queue by hand. **On deploy:** purge queued `scrape_batch` tasks (or let them drain) before announcing the fix. |
| W | Each new listing logs an `ERROR` line: the "does this URL exist?" lookup answers 404 when it doesn't, which is the normal case. | Real errors drown in noise. | ✅ The lookup treats 404 as "new listing" without logging an error. |

## Test results (local)

| Suite | Result |
|---|---|
| Backend (pytest) | 715 passed |
| Scrapers (pytest) | 339 passed, 1 failed (`test_proxy` reads the placeholder proxy user from the container's `.env`; unrelated to this branch) |
| Frontend unit (vitest) | 76 passed |
| E2E (Playwright, Chrome) | 51 passed, including the 14 user stories |

## Not covered

- **B** is covered by backend tests and mocked UI stories; a run against the live marketplaces depends on the sites, so it is not part of the suite. It was checked by hand on 2026-11-04: *Run now* for "python fluente" found 13 listings, checked 13, kept 7 that match the term and closed as `success` in about 90 s (screenshots `en-09-run-now.png` and `en-09b-run-finished.png`).
- **P** and **S** are open, as explained above. **V** needs a step in the deploy.
