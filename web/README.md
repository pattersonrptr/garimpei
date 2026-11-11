# Garimpei web (public pages)

The public comparator pages, in Next.js (App Router, server-rendered). It reads
the backend's public book API (`/books`), never the database. See
`docs/plan/phase-3-public-pages.md`.

## Run

With the rest of the stack:

```bash
docker compose up -d site      # http://localhost:3000
```

Locally, against an API on port 8000:

```bash
npm install
API_URL=http://localhost:8000 npm run dev
```

## Check

```bash
npm run typecheck
npm run test     # vitest, pure helpers in src/lib
npm run build
```

## Layout

- `src/app`: routes (`/`, `/busca`, `/livro/<isbn13>-<slug>`, `sitemap.xml`,
  `robots.txt`). Server components fetch on the server.
- `src/lib/api.ts`: the only place that talks to the backend (server only).
- `src/lib/format.ts`: money, "updated X h ago", store names, book URLs.
- `src/lib/chart.ts`: the price chart's geometry (pure; the SVG is drawn on
  the server).
- `src/lib/seo.ts`: site URL and schema.org data.

Environment: `API_URL`, `SITE_URL`, `AMAZON_ASSOCIATE_TAG` (optional).
- `src/app/globals.css`: the Phase 0 tokens (`docs/plan/visual-direction.md`).
