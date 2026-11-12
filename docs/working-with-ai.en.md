# How I work with AI on this project

> 🇧🇷 [Leia em português](working-with-ai.md) (the original; this is a translation).

Garimpei is a price comparator I am building for myself and, if it works out,
for other people. I started by writing the code by hand, with an architecture I
designed. Today I develop with Claude Code: I decide the product and the
architecture, the AI proposes, implements and verifies, and nothing reaches
`main` without passing automated tests, CI and my own validation.

**Why this document exists:** I want to record how I work with AI, to learn from
it and take what works to other projects. It also shows, with real examples,
what I know and how I work: what is mine, what came from the AI, how I check
the result and where the AI got it wrong.

---

## 1. The problem and the limits

**The problem:** when I want to buy something, especially a book, I have to
open several stores, compare new and used, and guess whether today's price is
good or whether it is worth waiting. Garimpei puts new and used offers side by
side, keeps the price history, says whether the price is "good", "normal" or
"high right now", and sends an e-mail when the price reaches the value I want.

**Why books first:** the ISBN makes it almost trivial to know that two listings
in different stores are the same product, and that is the hardest part of a
comparator. A wrong match is worse than none. Books also have free metadata
(BrasilAPI) and a strong used market (Estante Virtual, OLX, Enjoei). The data
model was generic from day one (product, identifier, offer) so other
categories can come later.

**It is also a study project:** I chose FastAPI and Clean Architecture to
consolidate both, and moving to the cloud will be my way to learn AWS.

**The limits, honestly:**

- There are no real users and no production deployment yet; everything runs
  locally.
- Password reset and a welcome e-mail do not exist in this repository.
- For now the goal is something that works for me and is ready for other
  people, with no commercial launch planned. That is why, from the start, the
  architecture supports many users (accounts, plans, per-user alerts): when
  more people arrive, the foundation is ready for them.

## 2. How I got here

It is a side project, done in about 5 hours a week, alongside my job and other
personal projects. The pace in the table reflects that.

| When | What happened |
|---|---|
| Dec 2025 | First commits, written by hand, with no AI at all (not even Copilot). The first commit (Dec 7) already had a repository with an interface, use cases and a validator |
| Dec 13, 2025 | Restructured to follow Clean Architecture more closely, which I was studying |
| Feb 2026 | Unit, integration and end-to-end tests, and CI on GitHub Actions. My idea and my decision |
| Until Apr 2026 | I used GitHub Copilot; in April I ran an experiment with Qwen |
| Apr 2026 | I merged the back end and the front end, which were separate repositories, into this monorepo |
| Oct 2026 | I started using Claude Code (first commit it co-signed: Oct 24) |
| Nov 2026 | Change of direction: from a "keyword deal monitor" to a price comparator. Planned on Nov 9 and delivered in small slices, one per PR, during the month |

## 3. Who does what

**Me:**

- I decide the product: what to build, in what order and what stays out;
- I design and look after the architecture;
- I define the testing strategy and the safety layers (section 8);
- I answer the rounds of questions in each plan and approve it;
- I test the result as a user and say what needs to change.

**Claude Code:**

- proposes plans with questions, for me to decide;
- suggests paths and points out what it thinks is wrong, including in what I
  asked for;
- implements in small slices, one PR per slice;
- runs the tests, brings up the local environment, takes mobile and desktop
  screenshots;
- merges on its own once CI is green, with the evidence in the PR.

In practice it works like pair programming: I have the final word, but the
decisions come out of the conversation.

### The architecture

The project is my own implementation of Clean Architecture: the domain at the
center, dependencies pointing inward, details (database, framework, e-mail) at
the edges. I keep my own notes on Clean Architecture and other software
engineering topics, and the AI reads them to understand how I think about the
architecture before it proposes changes. The rules that come from them are in
the [main plan](plan/README.md#4-architecture-rules).

Some of these principles were in the code before any AI:

| Idea | Where it is | Since |
|---|---|---|
| **Repository** with an interface (the use case depends on the interface, not on the database) | `UserRepositoryInterface` and its SQLAlchemy implementation | 1st commit, Dec 7, 2025 |
| **Use case**: one class per action (single responsibility, the "S" in SOLID) | `CreateUserUseCase`, `GetUserByIdUseCase`, … | 1st commit |
| **Validator** separate from the business rules | `UserValidator` | 1st commit |
| **Presenter**: the response format (JSON:API) outside the controller | `UserPresenter` and the others | Dec 13, 2025 |
| **Dependency injection** | FastAPI's `Depends(...)` wiring repositories and use cases | from the start |
| **Strategy**: swap the implementation without changing the caller (the "O" in SOLID) | `EmailServiceInterface` with SMTP or SendGrid; `IsbnMatcher` to match offers per category | 2026 |
| **Ports and adapters**: the module that needs something defines the interface (port); another module provides the adapter | `alerts` defines `ProductSnapshotReader` and `BookFinder`; the adapter is built over `catalog` | Nov 2026 |

**Ports** are interfaces: used with dependency injection, they keep modules
isolated, because anything that implements the interface can be plugged in.
That is the "D" in SOLID (dependency inversion). **Adapters** (the Adapter
pattern) shield the domain from details. All of this makes testing easier: a
use case is tested with a fake adapter, with no database.

The code has a few tactical Domain-Driven Design patterns (entities,
repositories, modules named after the domain), but they came from Clean
Architecture, which shares those ideas, not from studying DDD. I have not read
about DDD yet; it is on my list.

Since Nov 2026 the back end is being reorganized by domain (`catalog`,
`alerts`), the so-called *screaming architecture*: the folders say what the
system does, not which framework it uses. The move happens in small steps, one
module per PR, without stopping the rest of the work.

**Tools:** FastAPI, SQLAlchemy and Alembic with PostgreSQL in the back end;
Celery with Redis in the collectors; Next.js for the public site; React with
Vite for the admin panel; everything running on Docker Compose.

## 4. The work cycle

A real example: Phase 5, which moved the user area to the new site.

1. **A plan with questions.** Claude surveys what exists and asks me a round of
   questions. For example: sign in by e-mail, by username or both? What does
   "Meus alertas" (My alerts) need to show? I answer, and the answers become
   decisions recorded in [`docs/plan/phase-5-user-area.md`](plan/phase-5-user-area.md).
2. **Small slices, one PR each:** account API (#90), session (#91), alerts
   (#92), account (#93), admin for administrators only (#94), wrap-up (#95).
3. **Verification before merging:** unit tests, type check, build,
   end-to-end browser tests against the local environment, and screenshots.
4. **Merge on green CI.** Since Nov 11, 2026 the AI merges on its own once
   every CI check passes; if something is red, it fixes it first. I stopped
   being the bottleneck for green PRs: branch protection on GitHub refuses a
   merge without the checks, even for me. My validation is now using the
   system and pointing out what needs to change, and product and architecture
   decisions are still mine.
5. **The plan is updated** with every slice, with the new decisions.

When the direction changes midway, the plan changes with it. Phase 5 itself
started that way: I tested Phase 4's "Me avise" (Warn me) button and landed on
an old interface that did not match the rest. I stopped, and we decided to
move the user area.

## 5. Some decisions explained

### A Next.js site, not just the React (Vite) app

- **Context:** the project started with a React (Vite) app built for keyword
  alerts. It runs in the user's browser: pages arrive empty and JavaScript
  builds them.
- **Why change:** a comparator lives on public pages (search, book page) that
  Google needs to read and that must open fast on a phone. Next.js serves those
  pages ready-made from the server (SSR), which helps SEO and speed. It was the
  AI's suggestion during planning, and I agreed.
- **How:** no big-bang migration. The site started with the public pages only
  (Phase 3); the user area came later (Phase 5).
- **Remaining limitation:** the admin panel is still in the old app, with a
  different look. **Next step:** move the admin to Next too, with the same
  identity, and retire Vite.

### Only collect from those who allow it

- **Rule:** I do not scrape stores whose terms forbid it, such as Amazon.
  Amazon comes in through the affiliate program: today with a search link, and
  with prices through the official API once the affiliate account meets the
  requirements.
- **Why:** besides the terms of use, scraping a store I am an affiliate of can
  cost me the affiliate account.
- **Remaining limitation:** without Amazon's new price in the comparison, the
  page shows the affiliate search link instead.

### Collect politely

- **Rule:** collectors use plain HTTP requests whenever the price is in the
  HTML, and a browser only when the page depends on JavaScript. They respect
  `robots.txt`, pause 5 to 15 seconds between requests and stop a store for the
  day at the first block. They do not bypass captchas or use proxies.
- **Rejected alternative:** working around blocks to collect from more stores.
- **Why:** to avoid legal risk and IP bans. I prefer fewer stores to abusive
  collection.

### A session cookie JavaScript cannot read

- **Decision:** on the site, the login token lives in an `httpOnly` cookie,
  written only by the server, not in `localStorage`.
- **Why:** a malicious script on the page cannot read the token.
- **Cost:** token renewal goes through the Next server, which was more work
  than keeping it in the browser.

### Refactor gradually, never all at once

- **Decision:** the reorganization by domain goes one module per PR, with no
  behavior change, and the front-end move goes page by page.
- **Rejected alternative:** rewriting everything at once.
- **Why:** each small step is testable and reversible, and the project keeps
  working along the way.

## 6. How I verify

I decided early that the project would have many tests. Today:

| Part | Tests | Tool |
|---|---|---|
| Back end (API) | 884 | pytest |
| Collectors | 313 | pytest |
| Public site | 75 | Vitest |
| Admin panel | 75 | Vitest |
| End to end (browser) | 32 | Playwright |

- **CI:** on every PR, GitHub Actions runs lint, type checks, tests and build
  for each part. A merge happens only when everything is green.
- **End-to-end (E2E) tests:** Playwright opens a browser and does what a user
  would: opens a book, clicks "Me avise", signs in, creates the alert, checks
  the card and the e-mail that arrives in Mailpit (a fake local mailbox).
  **They still run only locally**, before each merge, not in CI.
- **Manual:** mobile and desktop screenshots for every visual change, and I
  use the system for real. The README's screenshots and video come from a
  Playwright script ([`frontend/e2e/media/`](../frontend/e2e/media/tour.media.ts)),
  so they can be taken again when the screens change.
- **Not tested yet:** load (many users at once), real e-mail delivery outside
  the fake mailbox, and anything in production.

## 7. Where the AI got it wrong, and who caught it

The AI makes mistakes. What matters is having barriers that catch them before
`main`.

### Caught by the automated barriers

| The mistake | What caught it | What changed |
|---|---|---|
| When editing with scripts, it changed line endings (CRLF/LF) and inflated the diffs | Reviewing the diff | Written rule: keep each file's own line endings |
| Book alerts were rejected by the free plan's limit | End-to-end test with the free-plan account | Fixed one-day frequency for book alerts (#87) |
| Tests assumed "401" where the API returns "400" (bad login) and "403" (no token) | The tests themselves failed | Adjusted to the real, documented behavior (#90) |
| The site would send users to sign in on any "403", including "plan limit" | Reading the controller before implementing | Only "401" asks to sign in again; "403" becomes a message (#92) |
| The ruff (formatter) hook left an extra blank line | Testing the hook before publishing it | Order fixed (#96) |
| E2E tests with guessed labels and a collapsed menu | The failure screenshot | Selectors use the real labels (#98) |
| `pre-commit run --all-files` changed old files, including an already-applied migration | `git status` before committing | Changes reverted; configuration adjusted (#97) |
| The hook that blocks `--no-verify` blocked the very commit that created it, because the message mentioned the flag | The hook itself, once active | It now looks only at the arguments of real git commands (#101) |
| The screenshot script clicked the top bar's "Buscar" (Search) button instead of "Entrar" (Sign in) | The failure screenshot the script itself saves | Selector scoped to the sign-in form (#102) |
| The demo video was 1.4 MB, over the repository's file size limit | pre-commit (`check-added-large-files`) | The script compresses the video with ffmpeg (#110) |
| The `docker-compose.override.yml` example uses the `!override` tag, which is not plain YAML | pre-commit (`check-yaml`) | The file is left out of that check; `docker compose config` validates it (#105) |
| The media script picked a book with no cover and a new copy at R$ 750 on its own | Looking at the screenshots before publishing | The book in the screenshots is now fixed and configurable (#110) |
| The alert e-mail still had the old app's look (blue, "R$ 17.46", `estante_virtual`) | Looking at the e-mail screenshot for the README | E-mail with Garimpei's identity (#111) |

### Caught by me

| The mistake | How I noticed | What changed |
|---|---|---|
| The AI framed the product as "for readers" | Reading the texts and the plan | Recorded rule: a general comparator; books are only the first category |
| "Me avise" led to the old app, with a different look and different logic | Using the system as a user | It became Phase 5: the whole user area on the new site |
| The admin panel still showed "Meus alertas" and "Planos" (Plans), user screens | Browsing the panel | Those screens left the admin (#98) |

### One case in detail: the alert the free plan blocked

- **The problem:** the "Me avise" button created an alert with the default
  frequency of the old alerts (every 60 minutes). The free plan does not allow
  that frequency, and the API answered "plan limit reached". The unit tests
  passed, because they used another account.
- **How it showed up:** in the end-to-end test, with the free-plan customer
  account, the alert was not created.
- **The investigation:** the frequency only makes sense for keyword searches.
  Books are collected once a day and the alert is checked when a new offer
  arrives.
- **The fix:** book alerts use a fixed one-day frequency, and the end-to-end
  test now covers that path.
- **The check:** the same test again, with the e-mail arriving in Mailpit.

## 8. The safety layers

There is an important difference between them: `AGENTS.md` is an
**instruction**. The AI follows it, but nothing stops it from deviating, and I
can even ask it to ignore a rule. Permissions and hooks are **locks**: Claude
Code enforces them, not the model, so the AI cannot skip them. And all of that
applies only to the AI: the protections on GitHub apply to everyone.

| Layer | What it catches | What it does not |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) (read by Claude through `CLAUDE.md`) | Departures from the house rules: architecture, one slice per PR, how to verify, known traps | Nothing by force: it is an instruction, not a lock |
| Permissions ([`.claude/settings.json`](../.claude/settings.json)) | `docker compose down` and migrations ask for my confirmation; editing `.env` and fetching Amazon are denied. Pushing a work branch and merging a PR are free, because the locks below already protect `main` | Commands not on the list (a `curl` to Amazon, for example) |
| Hooks ([`.claude/hooks/`](../.claude/hooks/)) | They block: edits to `.env` and to migrations already on `main`; commits or pushes on `main`, force pushes, skipping pre-commit and forced merges. They ask me before any change to the locks themselves (`.claude/`). They fix Python formatting | Logic errors |
| pre-commit | Code quality: formatting, invalid JSON/YAML, leftover conflict markers, in my commits and the AI's | Behavior |
| Branch protection on GitHub | Applies to everyone, me included: `main` changes only through a PR with the four CI checks green, no force push, no deleting `main`. It is what lets the AI merge on its own | What the PR contains |
| CI (GitHub Actions) | Lint, types, tests and build for each part, on every PR | Full browser flows (E2E does not run there yet) |
| E2E tests | Real user flows, from the click to the e-mail | They run only locally, when someone runs them |
| Skill [`e2e-local`](../.claude/skills/e2e-local/SKILL.md) | The end-to-end check as a recipe: what to rebuild, waiting for the services, running Playwright, taking screenshots | It runs only when called |
| Skill [`dependabot-triage`](../.claude/skills/dependabot-triage/SKILL.md) | Triage of the Dependabot PRs: a script gathers the CI results and errors, and the skill decides between merging, fixing, or closing with an ignore rule | It runs only when called |
| Subagent [`architecture-reviewer`](../.claude/agents/architecture-reviewer.md) | Violations of my architecture rules in a diff (dependency rule, ports, pure entities) | Bugs and style; it is a second opinion, not a lock |
| My validation | Whether it makes sense for the product; what no test measures | It depends on me reviewing carefully |

### Automate what repeats

I only turn into a skill, subagent or hook what I already do by hand again and
again (YAGNI): nothing goes in just to show I can configure it. Besides
avoiding mistakes, this saves tokens. The session-start brief is a script that
gives, in four lines, the branch, the open PRs and what is left in the plan,
instead of the AI looking that up every session. The end-to-end skill already
carries the steps and the known traps. When the AI notices a repeated task, it
proposes the automation and the right model: a cheaper one for mechanical
steps, a stronger one for reviews.

## 9. What I master and what I am still studying

Following advice I read: if I do not yet understand part of the generated code,
I go back to it before presenting it as something I master.

- **I can explain well:** the front end, requests, endpoints and controllers,
  how FastAPI works, and the architecture (use cases, repositories, ports and
  adapters, dependency injection).
- **I can explain the concept, but need to refresh the tool:** queues and
  brokers (Celery with Redis).
- **I need to study:** the cookie session in Next.js and the price verdict rule
  (it compares today's lowest price with the 25th and 75th percentiles of the
  last 90 days), which was the AI's idea and which I approved. I also want to
  read about Domain-Driven Design.

This document will change along with the project and with what I learn. When
something here gets out of date, the AI proposes the change and I review it
first.

## 10. Next steps

Each with a "done when" criterion. The full plan is in
[`docs/plan/README.md`](plan/README.md).

| Next step | Done when… |
|---|---|
| Run the E2E tests in CI | A PR that breaks the "Me avise" flow turns red on its own |
| Move the admin to Next.js, with Garimpei's identity | The old app (Vite) can be deleted and the admin tests pass on the site |
| Password reset and a welcome e-mail | A user gets the e-mail, changes the password and signs in with the new one |
| Move to AWS | The site runs outside my machine, within the cost limit I set |
| Study the cookie session and the verdict rule | I can explain each one in a minute, without looking at the code |
