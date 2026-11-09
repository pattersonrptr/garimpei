/**
 * Customer stories: what a real Free-plan customer does, and what they must see.
 *
 * Each test reads as a story ("the customer does X; they see Y"). The letters
 * in the titles point to the findings table in docs/qa/exploratory-report.md.
 *
 * Data is seeded through the real API (see fixtures.ts) and removed before
 * every story, so the stories run in any order and leave nothing behind.
 */

import { CUSTOMER, PRODUCT_PREFIX, TERM_PREFIX, api, expect, login, mailpit, test } from '../fixtures'

const TERM = `${TERM_PREFIX} fluent`
const MATCHING_PRODUCT = `${PRODUCT_PREFIX} Fluent Python, 2nd edition`
const OTHER_PRODUCT = `${PRODUCT_PREFIX} Cookbook nobody asked for`

test.describe('Customer stories', () => {
  test.beforeEach(async () => {
    await api.reset()
  })

  test.afterAll(async () => {
    await api.reset()
  })

  test('L/D/K/M: creating an alert explains the plan rules and the max price before anything fails', async ({
    customerPage: page,
  }) => {
    await page.goto('/alerts')
    await page.getByRole('button', { name: 'New Alert' }).click()
    const dialog = page.getByRole('dialog')

    // D: the customer understands what "max price" does
    await expect(dialog.getByText(/notified when a listing costs this much or less/i)).toBeVisible()
    // L: the plan minimum is shown up front and is the default
    await expect(dialog.getByText(/your free plan checks every 360 minutes at most/i)).toBeVisible()
    await expect(dialog.getByLabel('Check frequency (minutes)')).toHaveValue('360')

    // K: the sources field has an accessible name; M: sites have readable names
    await dialog.getByRole('combobox', { name: 'Source websites' }).click()
    await expect(page.getByRole('option', { name: 'Estante Virtual' })).toBeVisible()
    await expect(page.getByRole('option', { name: 'estante_virtual' })).toHaveCount(0)
    await page.getByRole('option', { name: 'Estante Virtual' }).click()
    await page.keyboard.press('Escape')

    // L: asking for more than the plan allows says why, inside the form
    await dialog.getByLabel('Search term (keyword)').fill(TERM)
    await dialog.getByRole('spinbutton', { name: 'Max price' }).fill('80')
    await dialog.getByLabel('Check frequency (minutes)').fill('30')
    await dialog.getByRole('button', { name: 'Create' }).click()
    await expect(dialog.getByRole('alert')).toContainText(/360 minutes/)
    await expect(dialog.getByRole('link', { name: /see plans/i })).toBeVisible()

    // Fixing it creates the alert, shown with the site's readable name
    await dialog.getByLabel('Check frequency (minutes)').fill('360')
    await dialog.getByRole('button', { name: 'Create' }).click()
    await expect(dialog).toBeHidden()
    const row = page.getByRole('row').filter({ hasText: TERM })
    await expect(row).toContainText('Estante Virtual')
  })

  test('L: the fourth alert on the Free plan explains the limit and how to get more', async ({
    customerPage: page,
  }) => {
    for (const n of [1, 2, 3]) await api.createCustomerAlert(`${TERM_PREFIX} limit ${n}`, 50)

    await page.goto('/alerts')
    await page.getByRole('button', { name: 'New Alert' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Search term (keyword)').fill(`${TERM_PREFIX} limit 4`)
    await dialog.getByRole('spinbutton', { name: 'Max price' }).fill('50')
    await dialog.getByRole('button', { name: 'Create' }).click()

    await expect(dialog.getByRole('alert')).toContainText(/3 active alerts/)
    await expect(dialog.getByRole('link', { name: /see plans/i })).toBeVisible()
  })

  test('E/F/G: the products page shows only what my alerts found, and its tools work', async ({
    customerPage: page,
  }) => {
    await api.seedProduct(MATCHING_PRODUCT, 120)
    await api.seedProduct(`${PRODUCT_PREFIX} Fluent Python, pocket edition`, 40)
    await api.seedProduct(OTHER_PRODUCT, 10)
    await api.createCustomerAlert(TERM, 50)

    await page.goto('/products')
    const grid = page.getByRole('grid')
    // E: only listings that match one of my alerts
    await expect(grid).toContainText(MATCHING_PRODUCT)
    await expect(grid).not.toContainText(OTHER_PRODUCT)
    await expect(page.getByText(/1–2 of 2/)).toBeVisible()

    // F: the title filter really filters
    await page.getByRole('button', { name: 'Filters' }).click()
    await page.getByRole('textbox', { name: 'Title' }).fill('pocket')
    await expect(grid).not.toContainText('2nd edition')
    await expect(grid).toContainText('pocket edition')
    await page.getByRole('button', { name: 'Clear' }).click()

    // Opportunities only: the R$ 40 listing is under my R$ 50 limit
    await page.getByRole('checkbox', { name: /opportunities only/i }).check()
    await expect(grid).toContainText('pocket edition')
    await expect(grid).not.toContainText('2nd edition')
  })

  test('Q: a product page tells me which alert found it and how much I save', async ({
    customerPage: page,
  }) => {
    const productId = await api.seedProduct(MATCHING_PRODUCT, 40)
    await api.createCustomerAlert(TERM, 50)

    await page.goto(`/products/${productId}`)
    const section = page.getByRole('region', { name: /your alerts/i })
    await expect(section).toContainText(TERM)
    await expect(section).toContainText(/opportunity/i)
    await expect(section).toContainText(/R\$\s?10\.00 below your max price/)
  })

  test('C: raising the max price finds the listings already collected, and emails me', async ({
    customerPage: page,
  }) => {
    await api.seedProduct(MATCHING_PRODUCT, 120)
    await api.createCustomerAlert(TERM, 50)

    await page.goto('/dashboard')
    await expect(page.getByText(MATCHING_PRODUCT)).toHaveCount(0)

    await page.goto('/alerts')
    const row = page.getByRole('row').filter({ hasText: TERM })
    await row.getByRole('button', { name: 'Edit' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('spinbutton', { name: 'Max price' }).fill('150')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    await page.goto('/dashboard')
    await expect(page.getByText(MATCHING_PRODUCT)).toBeVisible()
    await expect.poll(async () => (await mailpit.search(TERM)).length, { timeout: 15_000 }).toBe(1)
  })

  test('I: with alerts in place, the dashboard shows results instead of onboarding text', async ({
    customerPage: page,
  }) => {
    await api.seedProduct(MATCHING_PRODUCT, 40)
    await api.createCustomerAlert(TERM, 50)

    await page.goto('/dashboard')
    await expect(page.getByText(/create alerts to start/i)).toHaveCount(0)
    await expect(page.getByText(/create your first alert/i)).toHaveCount(0)
    const opportunities = page.getByRole('region', { name: /opportunities/i })
    await expect(opportunities).toContainText(MATCHING_PRODUCT)
    await expect(opportunities).toContainText(/save R\$\s?10\.00/i)
  })

  test('B: opening the alerts page during a search shows its progress', async ({
    customerPage: page,
  }) => {
    await api.createCustomerAlert(TERM, 50)
    // A search started earlier (by the schedule, or in another tab)
    await page.route(/\/search-configs\/\d+\/execution-status$/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            type: 'execution_status',
            id: '1',
            attributes: {
              status: 'running',
              started_at: '2026-11-04T10:00:00',
              finished_at: null,
              listings_found: 12,
              listings_checked: 5,
              results_count: 1,
              error_message: null,
            },
          },
        }),
      }),
    )

    await page.goto('/alerts')
    const row = page.getByRole('row').filter({ hasText: TERM })
    await expect(row).toContainText(/checking 5 of 12 listings/i)
  })

  test('B/J: "Run now" works on a paused alert and reports what the search found', async ({
    customerPage: page,
  }) => {
    await api.createCustomerAlert(TERM, 50)
    // The real search scrapes a marketplace for minutes; the story checks what
    // the customer sees, so the trigger and the status are answered here.
    let triggered = false
    let polls = 0
    await page.route(/\/search-configs\/\d+\/trigger$/, (route) => {
      triggered = true
      return route.fulfill({ status: 202, contentType: 'application/json', body: '{"data":{"type":"task","id":"t","attributes":{}}}' })
    })
    // Before "Run now" the page reads the last run (a finished one); after it,
    // the first polls see the run in progress and later ones see it finished.
    await page.route(/\/search-configs\/\d+\/execution-status$/, (route) => {
      if (triggered) polls += 1
      const done = !triggered || polls > 2
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            type: 'execution_status',
            id: '1',
            attributes: {
              status: done ? 'success' : 'running',
              started_at: '2026-11-04T10:00:00',
              finished_at: done ? '2026-11-04T10:03:00' : null,
              listings_found: 12,
              listings_checked: done ? 12 : 5,
              results_count: done ? 3 : 1,
              error_message: null,
            },
          },
        }),
      })
    })

    await page.goto('/alerts')
    const row = page.getByRole('row').filter({ hasText: TERM })
    await row.getByRole('button', { name: 'Pause' }).click()
    await expect(row).toContainText('Paused')

    // J: pausing stops the schedule, not the manual search
    const runNow = row.getByRole('button', { name: 'Run now' })
    await expect(runNow).toBeEnabled()
    await runNow.click()
    await expect(page.getByText(/search started/i)).toBeVisible()
    // B: progress while it runs, and a summary when it ends
    await expect(row).toContainText(/checking 5 of 12 listings/i, { timeout: 15_000 })
    await expect(page.getByText(/search finished: 12 listings checked, 3 match your term/i)).toBeVisible({
      timeout: 20_000,
    })
  })

  test('O: a mistyped address shows a "page not found" page', async ({ page }) => {
    await page.goto('/this-page-does-not-exist')
    await expect(page.getByRole('heading', { name: /page not found/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /go to the home page/i })).toBeVisible()
  })

  test('the customer can sign in with the account from .env', async ({ page }) => {
    expect(CUSTOMER.password, 'E2E_USER_PASSWORD is missing from .env').not.toBe('')
    await login(page, CUSTOMER.username, CUSTOMER.password)
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })
})
