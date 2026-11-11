# Phase 5: user area in Next.js (plan)

Draft, Nov 11, 2026. Goal from the main plan: **a user never sees the Vite
app; everything a user does has the Garimpei look.** The Vite app becomes the
admin back office.

## Why

Trying "warn me" (Phase 4) dropped the user into the old Vite app: another
look, and screens made for keyword alerts (stores, frequency in minutes,
"search now", Dashboard, Products). Books are the first category of a
general comparator, so names and screens stay generic (product, user).

## Slices (in order, one PR each)

| # | Slice | Done when |
|---|---|---|
| 5a | **Backend: account and "my alerts"** (done, #90). Login by e-mail or username, `GET /auth/me`, `PUT /auth/password`, `GET /me/alerts` | The API gives a user their account and their product alerts with today's price, the verdict and the e-mails sent |
| 5b | **Next.js session** (done). `/entrar`, `/cadastro`, sign out, token in an httpOnly cookie, renewed in `proxy.ts` | A user signs up, signs in and out on the Garimpei site |
| 5c | **"Warn me" and "My alerts" in Next.js** (done). `/alertas/novo`, `/alertas` (price vs target, verdict, notices; pause, change price, delete) | A user creates and manages alerts without the Vite app |
| 5d | **Account.** `/conta`: username and e-mail, change password, sign out | |
| 5e | **Vite admin-only.** Non-admins are sent to the site; register, landing and the user screens leave Vite; no "create user" in admin | A non-admin never lands in Vite |
| 5f | **Close.** Plan updated; propose refreshing the READMEs (root has old screenshots and diagrams) | |

## Decisions (Nov 11, 2026)

1. **Sign in with e-mail or username.** A value with "@" is looked up as an
   e-mail, ignoring case. Sign-up still asks for username, e-mail and
   password.
2. **Session:** the backend JWT lives in an httpOnly cookie
   (`garimpei_session`, SameSite=Lax, Secure on https) written by Server
   Actions; nothing in localStorage. The Next.js server calls the backend
   with `Authorization: Bearer`. `proxy.ts` (Next 16 middleware) renews the
   token on the account routes when less than 10 minutes are left. No token:
   the API answers **403**; an expired or bad one: **401**. Both mean "sign
   in again" (`/entrar?next=…`, in-app paths only).
3. **Routes in Portuguese**, like `/livro` and `/busca`: `/entrar`,
   `/cadastro`, `/alertas`, `/alertas/novo`, `/conta`.
4. **The top bar always shows "Meus alertas"** and does not read the cookie,
   so public pages stay static and cacheable.
5. **"My alerts" shows only product alerts.** Keyword alerts stay in the
   backend and in admin. Active first, then newest.
6. **`GET /me/alerts`** (module `alerts`): per alert, the product (category,
   title, ISBN, cover), today's lowest price in the alert's condition with its
   store (for "any": the cheaper of new and used) and that condition's
   verdict, and the e-mails sent (latest 5 with date and store, plus the
   total). The product comes through a `ProductSnapshotReader` port defined in
   `alerts`, implemented over the catalog. Notice history is two queries for
   all alerts (no N+1); the catalog read is one per product (a user has a
   handful of alerts).
7. **Notices show date and store, not the price**: the notification log does
   not store the price as a number (only inside the subject). Add a column
   later if the price turns out to matter.
8. **Password change** needs the current password; the new one needs at
   least 8 characters. `/auth/me` and `/auth/password` live in the old auth
   controller until the `accounts` module is refactored.
9. **Password reset** stays out (checklist before other people use it).
10. **Only a 401 sends the user to sign in again** (5c). The site always
    sends a token, so a 403 from the API means "not allowed" (for example
    the plan's active-alert limit) and is shown as a message.
11. **Alert actions are plain forms** (5c): pause/resume and delete work
    without JavaScript; delete asks a second time inside a `<details>`, never
    with `confirm()`. Changing the price uses a small client form for inline
    errors.
