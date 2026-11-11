/**
 * Shared Playwright fixtures for E2E tests.
 *
 * Accounts come from the repository's `.env` (never hard-coded):
 *   E2E_ADMIN_USERNAME / E2E_ADMIN_PASSWORD  - a superuser
 *   E2E_USER_USERNAME  / E2E_USER_PASSWORD   - a regular customer (Free plan),
 *     who uses the public site (E2E_SITE_URL), not this back office
 * Environment variables with the same names take precedence.
 *
 * Provides:
 * - `login` helper (UI login) and `authenticatedPage` (logged in as admin)
 * - `api` helpers to seed and clean test data through the real API
 * - `mailpit` helpers to read the emails the app sent (local Mailpit)
 */

import fs from 'node:fs'
import path from 'node:path'
import {
  test as base,
  expect,
  request,
  type APIRequestContext,
  type Page,
} from '@playwright/test'

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

function readDotEnv(): Record<string, string> {
  const file = path.resolve(process.cwd(), '..', '.env')
  if (!fs.existsSync(file)) return {}
  const entries = fs
    .readFileSync(file, 'utf8')
    .split(/\r?\n/)
    .filter((line) => line.includes('=') && !line.trimStart().startsWith('#'))
    .map((line) => {
      const i = line.indexOf('=')
      return [line.slice(0, i).trim(), line.slice(i + 1).trim()] as const
    })
  return Object.fromEntries(entries)
}

const dotEnv = readDotEnv()
const setting = (name: string, fallback = ''): string =>
  process.env[name] ?? dotEnv[name] ?? fallback

export const ADMIN_USER = {
  username: setting('E2E_ADMIN_USERNAME', 'admin'),
  password: setting('E2E_ADMIN_PASSWORD', 'admin'),
}

export const CUSTOMER = {
  username: setting('E2E_USER_USERNAME', 'e2e_user'),
  password: setting('E2E_USER_PASSWORD'),
}

export const API_BASE = setting('E2E_API_URL', 'http://localhost:8000')
export const MAILPIT_BASE = setting('E2E_MAILPIT_URL', 'http://localhost:8026')
/** The public site (Next.js), where users sign in and manage alerts. */
export const SITE_BASE = setting('E2E_SITE_URL', 'http://localhost:3000')

/** Prefix for every product the stories create, so cleanup finds them. */
export const PRODUCT_PREFIX = 'Garimpei E2E'
/** Prefix for every alert term the stories create. */
export const TERM_PREFIX = 'garimpei e2e'

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

/** Get an API auth token. */
export async function getAuthToken(
  username = ADMIN_USER.username,
  password = ADMIN_USER.password,
): Promise<string> {
  const ctx = await request.newContext()
  const resp = await ctx.post(`${API_BASE}/auth/login`, {
    form: { username, password, grant_type: 'password' },
  })
  if (!resp.ok()) throw new Error(`Login failed for ${username}: ${resp.status()}`)
  const body = await resp.json()
  await ctx.dispose()
  return body.data.attributes.access_token as string
}

/** The user id inside a token (JWT claim `user_id`). */
export function userIdOf(token: string): number {
  const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'))
  return Number(payload.user_id)
}

/** An authenticated API context for one account (admin by default). */
export async function apiContext(
  username = ADMIN_USER.username,
  password = ADMIN_USER.password,
): Promise<APIRequestContext> {
  const token = await getAuthToken(username, password)
  return request.newContext({
    baseURL: API_BASE,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
}

type Resource = { id: string; attributes: Record<string, unknown> }

/** Read every page of a JSON:API collection. */
async function listAll(ctx: APIRequestContext, url: string): Promise<Resource[]> {
  const items: Resource[] = []
  for (let offset = 0; ; offset += 100) {
    const resp = await ctx.get(url, { params: { limit: '100', offset: String(offset) } })
    if (!resp.ok()) break
    const page: Resource[] = (await resp.json())?.data ?? []
    items.push(...page)
    if (page.length < 100) break
  }
  return items
}

function jsonApi(type: string, attributes: Record<string, unknown>) {
  return { data: { type, attributes } }
}

export const api = {
  /** Id of a source website by its slug (e.g. "estante_virtual"). */
  async sourceId(slug: string): Promise<number> {
    const ctx = await apiContext()
    const sites = await listAll(ctx, '/source-websites/')
    await ctx.dispose()
    const site = sites.find((s) => s.attributes.name === slug)
    if (!site) throw new Error(`Source website not found: ${slug}`)
    return Number(site.id)
  },

  /** Create a product with one price point, as the scrapers would. */
  async seedProduct(title: string, price: number, sourceSlug = 'estante_virtual') {
    const sourceId = await api.sourceId(sourceSlug)
    const ctx = await apiContext()
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    const created = await ctx.post('/products/', {
      data: jsonApi('product', {
        title,
        url: `https://example.com/e2e/${slug}-${Date.now()}`,
        description: 'Product created by the E2E stories.',
        condition: 'used',
        seller_name: 'E2E Seller',
        is_available: true,
        source_website_id: sourceId,
      }),
    })
    expect(created.status(), await created.text()).toBe(201)
    const productId = (await created.json()).data.id as string
    const history = await ctx.post('/price-histories/', {
      data: jsonApi('price_history', { product_id: Number(productId), price }),
    })
    expect(history.status(), await history.text()).toBe(201)
    await ctx.dispose()
    return productId
  },

  /** Create an alert through the API, for the customer unless another account is given. */
  async createAlert(
    term: string,
    maxPrice: number,
    sourceSlugs = ['estante_virtual'],
    account = CUSTOMER,
    isActive = true,
  ) {
    const sourceIds = await Promise.all(sourceSlugs.map(api.sourceId))
    const token = await getAuthToken(account.username, account.password)
    const ctx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: { Authorization: `Bearer ${token}` },
    })
    const resp = await ctx.post('/price-alerts/', {
      data: jsonApi('price_alert', {
        search_term: term,
        max_price: maxPrice,
        user_id: userIdOf(token),
        is_active: isActive,
        frequency_minutes: 360,
        source_website_ids: sourceIds,
      }),
    })
    expect(resp.status(), await resp.text()).toBe(201)
    const id = (await resp.json()).data.id as string
    await ctx.dispose()
    return id
  },

  /** Shortcut for an alert owned by the customer. */
  async createCustomerAlert(term: string, maxPrice: number, sourceSlugs = ['estante_virtual']) {
    return api.createAlert(term, maxPrice, sourceSlugs, CUSTOMER)
  },

  /** Remove everything the stories created: customer alerts, their searches, test products. */
  async reset() {
    const customer = await apiContext(CUSTOMER.username, CUSTOMER.password)
    for (const alert of await listAll(customer, '/price-alerts/')) {
      await customer.delete(`/price-alerts/${alert.id}`)
    }
    await customer.dispose()

    const admin = await apiContext()
    const adminId = userIdOf(await getAuthToken())
    for (const alert of await listAll(admin, `/price-alerts/user/${adminId}`)) {
      if (String(alert.attributes.search_term ?? '').startsWith(TERM_PREFIX)) {
        await admin.delete(`/price-alerts/${alert.id}`)
      }
    }
    for (const config of await listAll(admin, '/search-configs/')) {
      if (String(config.attributes.search_term ?? '').startsWith(TERM_PREFIX)) {
        await admin.delete(`/search-configs/${config.id}`)
      }
    }
    for (const product of await listAll(admin, '/products/')) {
      if (String(product.attributes.title ?? '').startsWith(PRODUCT_PREFIX)) {
        await admin.delete(`/products/${product.id}`)
      }
    }
    await admin.dispose()
    await mailpit.clear(TERM_PREFIX)
  },
}

// ---------------------------------------------------------------------------
// Mailpit (local SMTP catcher)
// ---------------------------------------------------------------------------

type MailSummary = { ID: string; Subject: string; To: { Address: string }[] }

export const mailpit = {
  async search(text: string): Promise<MailSummary[]> {
    const ctx = await request.newContext()
    const resp = await ctx.get(`${MAILPIT_BASE}/api/v1/search`, {
      params: { query: `subject:"${text}"` },
    })
    const body = resp.ok() ? await resp.json() : { messages: [] }
    await ctx.dispose()
    return body.messages ?? []
  },

  async clear(text: string) {
    const ids = (await mailpit.search(text)).map((m) => m.ID)
    if (!ids.length) return
    const ctx = await request.newContext()
    await ctx.delete(`${MAILPIT_BASE}/api/v1/messages`, { data: { IDs: ids } })
    await ctx.dispose()
  },
}

// ---------------------------------------------------------------------------
// Legacy cleanup helpers (used by the older specs)
// ---------------------------------------------------------------------------

/** Delete all price alerts whose keyword starts with a given prefix. */
export async function cleanupTestAlerts(prefix = 'e'): Promise<void> {
  const ctx = await apiContext()
  for (const alert of await listAll(ctx, '/price-alerts/')) {
    if (String(alert.attributes.search_term ?? '').startsWith(prefix)) {
      await ctx.delete(`/price-alerts/${alert.id}`)
    }
  }
  await ctx.dispose()
}

/** Delete all source websites whose name starts with a given prefix. */
export async function cleanupTestWebsites(prefix = 'e2e-'): Promise<void> {
  const ctx = await apiContext()
  for (const item of await listAll(ctx, '/source-websites/')) {
    if (String(item.attributes.name ?? '').startsWith(prefix)) {
      await ctx.delete(`/source-websites/${item.id}`)
    }
  }
  await ctx.dispose()
}

/** Delete all search configs whose search_term starts with a given prefix. */
export async function cleanupTestConfigs(prefix = 'e2e-'): Promise<void> {
  const ctx = await apiContext()
  for (const item of await listAll(ctx, '/search-configs/')) {
    if (String(item.attributes.search_term ?? '').startsWith(prefix)) {
      await ctx.delete(`/search-configs/${item.id}`)
    }
  }
  await ctx.dispose()
}

// ---------------------------------------------------------------------------
// UI helpers and fixtures
// ---------------------------------------------------------------------------

/** Log in via the Login page UI. */
export async function login(
  page: Page,
  username = ADMIN_USER.username,
  password = ADMIN_USER.password,
): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByRole('textbox', { name: 'Password' }).fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/admin$/, { timeout: 10_000 })
}

/**
 * Extended test fixtures.
 *
 * `authenticatedPage` is logged in as the admin. Customers no longer use
 * this app (Phase 5e): their stories run on the site (book-alerts.spec.ts).
 */
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await login(page)
    // eslint-disable-next-line react-hooks/rules-of-hooks
    await use(page)
  },
})

export { expect }
