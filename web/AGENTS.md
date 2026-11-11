# web/ — the public Garimpei site (Next.js 16)

- **Next.js 16, App Router.** APIs changed from older versions: read the
  bundled docs in `node_modules/next/dist/docs` before relying on memory.
  - Middleware is now **`src/proxy.ts`** (Node runtime).
  - `cookies()`, `headers()` and `searchParams` are **async**.
- **Session:** the backend JWT lives in the httpOnly cookie
  `garimpei_session`, written only by Server Actions (`src/app/actions`).
  Page JavaScript never sees it. `lib/session.ts` calls the API with a
  Bearer token; only a **401** sends the user to `/entrar?next=…` (a 403
  with a token means "not allowed", e.g. a plan limit).
- `next=` accepts only internal paths (`lib/nextPath.ts`, open-redirect guard).
- **Public pages stay static/cacheable:** the top bar never reads the
  cookie. Account pages (`/alertas`, `/conta`) are dynamic.
- Routes and UI text are in **Portuguese** (`/entrar`, `/cadastro`,
  `/alertas`, `/alertas/novo`, `/conta`, `/livro/…`, `/busca`); code in English.
- Presentation rules are pure functions in `src/lib/*.ts` with Vitest tests
  next to them; keep logic there, not in components.
- Styles: one `src/app/globals.css` with design tokens on `:root`; no CSS
  framework.
- Forms: Server Actions + `useActionState`, so they work before JS loads.
  No `confirm()`: destructive actions ask a second time in the page.
