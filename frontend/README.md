# Product Tracker — Frontend

React + Vite + TypeScript frontend for the **Product Tracker** application.
Tracks product prices over time and manages scraping configurations.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Build | [Vite](https://vitejs.dev/) 7 |
| UI framework | React 19 + TypeScript 5 |
| Component library | [MUI v6](https://mui.com/) (Material UI + DataGrid) |
| Routing | React Router v6 |
| HTTP client | Axios (with JWT interceptor + refresh queue) |
| Charts | [Recharts](https://recharts.org/) |
| Notifications | [Notistack](https://notistack.com/) |
| Testing | Vitest + Testing Library |
| Auth tokens | jwt-decode |

---

## Features

### Authentication
- **Login** — JWT-based authentication with automatic token refresh
- **Register** — Public self-registration form (username, email, password)
- **Logout** — Confirmation dialog before signing out
- **Session expiry** — Automatic redirect to login on token expiry

### Products
- Server-side paginated and sortable DataGrid
- **Filter toolbar** — filter by title, condition, and availability
- **Inline edit modal** — edit title, URL, condition, availability, seller, description
- **Bulk delete** — select multiple rows with checkboxes and delete in one click
- Page size selector: 10 / 25 / 50 / 100
- View detailed price history per product

### Search Configurations
- Server-side paginated DataGrid
- **Create / edit modal** — search term, frequency, preferred time, active toggle, multi-select source websites
- **Delete** with confirmation dialog
- **Bulk delete** with checkboxes

### Source Websites
- Server-side paginated DataGrid
- **Create / edit modal** — name, base URL, active toggle
- **Delete** with confirmation dialog
- **Bulk delete** with checkboxes

### Users _(staff / superuser only)_
- Accessible only to users with `is_staff` or `is_superuser` flag (shown in sidebar)
- Staff: read-only view (username, email, flags, created date)
- Superuser: full CRUD — create users, edit flags, delete with confirmation, **bulk delete**

---

### Languages

Portuguese (Brazil, default) and English, with a language menu in the header. Adding a language needs no code changes: see [`src/i18n/README.md`](src/i18n/README.md).

## Architecture

```
src/
├── api/
│   ├── client.ts          # Axios instance — JWT interceptors, token refresh queue
│   ├── endpoints.ts       # All API URL constants in one place
│   └── jsonapi.ts         # JSON:API helpers (unwrapSingle, unwrapCollection, wrapPayload)
├── services/              # One file per resource — maps API <-> domain types
│   ├── authService.ts
│   ├── userService.ts
│   ├── productService.ts
│   ├── priceHistoryService.ts
│   ├── searchConfigService.ts
│   └── sourceWebsiteService.ts
├── hooks/                 # Reusable React hooks built on top of services
│   ├── usePaginatedResource.ts   # Generic paginated list hook
│   └── useProductDetails.ts
├── context/
│   └── AuthContext.tsx    # Auth state — exposes useAuth() with isStaff, isSuperuser, userId, username
├── components/
│   ├── common/            # Shared UI: ConfirmationDialog, GenericFormModal, PageHeader
│   └── layout/            # App shell: AppLayout, Header, Sidebar, Footer
├── pages/                 # One file per route
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── ProductsPage.tsx
│   ├── ProductDetailPage.tsx
│   ├── SearchConfigsPage.tsx
│   ├── SourceWebsitesPage.tsx
│   └── UsersPage.tsx
├── router/
│   └── index.tsx          # Route definitions + RequireAuth guard
├── types/                 # Shared TypeScript interfaces (barrel-exported from index.ts)
├── lib/
│   ├── logger.ts          # Structured logger (suppresses debug in production)
│   └── formatters.ts      # Date and currency formatters
└── tests/
    ├── setup.ts
    └── unit/              # Unit tests mirroring src/ structure
```

Data flow: `pages` -> `hooks` -> `services` -> `api/client` -> backend

---

## Prerequisites

- Node.js >= 18
- npm >= 9
- The [product-tracker backend](../product-tracker) running on `http://localhost:8000`

---

## Setup

```bash
# 1. Install dependencies
npm install

# 2. Configure the API base URL
cp .env.example .env
# Edit .env if your backend runs on a different address

# 3. Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

---

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | TypeScript check + production build (outputs to `dist/`) |
| `npm run preview` | Preview the production build locally |
| `npm test` | Run all unit tests once |
| `npm run test:watch` | Run tests in watch mode |
| `npm run test:coverage` | Run tests and generate coverage report |

---

## Running Tests

```bash
npm test
```

Coverage report is generated in `coverage/` as HTML and LCOV.

```bash
npm run test:coverage
open coverage/index.html
```

---

## Docker

### With Docker Compose (recommended)

```bash
# Start (builds the image automatically, serves on port 80)
docker compose up --build

# Use a custom backend URL
VITE_API_BASE_URL=https://api.mysite.com docker compose up --build

# Run in the background
docker compose up -d --build

# Stop
docker compose down
```

### Manual Docker build

```bash
# Build the image
docker build -t product-tracker-front .

# Run (serves on port 80)
docker run -p 80:80 product-tracker-front

# Pass a custom API URL at build time
docker build --build-arg VITE_API_BASE_URL=https://api.mysite.com -t product-tracker-front .
```

---

## API Contract

All backend responses follow the [JSON:API](https://jsonapi.org/) specification:

```json
// Single resource
{ "data": { "id": "1", "type": "product", "attributes": { ... } } }

// Collection
{ "data": [ ... ], "meta": { "total": 42 } }
```

The `src/api/jsonapi.ts` helpers handle unwrapping automatically — services always return plain domain objects.
