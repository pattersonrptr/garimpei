import { test, expect, cleanupTestAlerts, cleanupTestConfigs } from './fixtures'

test.describe('Alerts page', () => {
  test.beforeAll(async () => {
    await cleanupTestAlerts('e')
    await cleanupTestConfigs('ea-')
    await cleanupTestConfigs('ee-')
    await cleanupTestConfigs('ed-')
    await cleanupTestConfigs('ep-')
  })

  test.afterAll(async () => {
    await cleanupTestAlerts('e')
    await cleanupTestConfigs('ea-')
    await cleanupTestConfigs('ee-')
    await cleanupTestConfigs('ed-')
    await cleanupTestConfigs('ep-')
  })

  // The Free plan allows 3 active alerts: each test cleans up after itself.
  test.afterEach(async () => {
    await cleanupTestAlerts('e')
  })

  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/alerts')
    await expect(page.getByText('My Alerts')).toBeVisible()
  })

  test('displays the alerts page with header and new alert button', async ({
    authenticatedPage: page,
  }) => {
    await expect(page.getByRole('button', { name: /new alert/i })).toBeVisible()
  })

  test('opens the create alert modal', async ({
    authenticatedPage: page,
  }) => {
    await page.getByRole('button', { name: /new alert/i }).click()
    await expect(page.getByText('Create Alert')).toBeVisible()
    await expect(
      page.getByLabel(/search term/i),
    ).toBeVisible()
    await expect(page.getByRole('spinbutton', { name: /max price/i })).toBeVisible()
    await expect(page.getByLabel(/check frequency/i)).toBeVisible()
  })

  test('creates a new alert', async ({ authenticatedPage: page }) => {
    const alertName = `ea-${Date.now()}`

    await page.getByRole('button', { name: /new alert/i }).click()
    await page.getByLabel(/search term/i).fill(alertName)
    await page.getByRole('spinbutton', { name: /max price/i }).fill('500')
    // The lowest frequency the Free plan allows
    await page.getByLabel(/check frequency/i).fill('360')

    await page.getByRole('button', { name: 'Create' }).click()

    // Wait for snackbar confirmation
    await expect(page.getByText(/alert created/i)).toBeVisible({
      timeout: 5000,
    })

    // Verify the alert appears in the grid
    await expect(page.getByRole('gridcell', { name: alertName })).toBeVisible({
      timeout: 10000,
    })
  })

  test('edits an existing alert', async ({ authenticatedPage: page }) => {
    // Create an alert first
    const alertName = `ee-${Date.now()}`
    await page.getByRole('button', { name: /new alert/i }).click()
    await page.getByLabel(/search term/i).fill(alertName)
    await page.getByRole('spinbutton', { name: /max price/i }).fill('100')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/alert created/i)).toBeVisible({
      timeout: 5000,
    })

    // Wait for the row to appear in the grid
    await expect(page.getByRole('gridcell', { name: alertName })).toBeVisible({
      timeout: 10000,
    })

    // Find the row and click edit
    const row = page.getByRole('row').filter({ hasText: alertName })
    await row.getByRole('button', { name: /edit/i }).click()

    // Modal opens with pre-filled data
    await expect(page.getByText('Edit Alert')).toBeVisible()

    // Change max price
    const maxPriceField = page.getByRole('spinbutton', { name: /max price/i })
    await maxPriceField.clear()
    await maxPriceField.fill('200')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText(/alert updated/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('pauses and resumes an alert', async ({ authenticatedPage: page }) => {
    // Create an alert
    const alertName = `ep-${Date.now()}`
    await page.getByRole('button', { name: /new alert/i }).click()
    await page.getByLabel(/search term/i).fill(alertName)
    await page.getByRole('spinbutton', { name: /max price/i }).fill('100')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/alert created/i)).toBeVisible({
      timeout: 5000,
    })

    // Wait for the row to appear in the grid
    await expect(page.getByRole('gridcell', { name: alertName })).toBeVisible({
      timeout: 10000,
    })

    // Find the row and click pause
    const row = page.getByRole('row').filter({ hasText: alertName })
    await row.getByRole('button', { name: /pause/i }).click()
    await expect(page.getByText(/alert paused/i)).toBeVisible({
      timeout: 5000,
    })

    // Now resume
    await row.getByRole('button', { name: /resume/i }).click()
    await expect(page.getByText(/alert resumed/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('deletes an alert', async ({ authenticatedPage: page }) => {
    // Create an alert
    const alertName = `ed-${Date.now()}`
    await page.getByRole('button', { name: /new alert/i }).click()
    await page.getByLabel(/search term/i).fill(alertName)
    await page.getByRole('spinbutton', { name: /max price/i }).fill('100')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/alert created/i)).toBeVisible({
      timeout: 5000,
    })

    // Wait for the row to appear in the grid
    await expect(page.getByRole('gridcell', { name: alertName })).toBeVisible({
      timeout: 10000,
    })

    // Find the row and click delete
    const row = page.getByRole('row').filter({ hasText: alertName })
    await row.getByRole('button', { name: /delete/i }).click()

    // Confirm the deletion dialog
    await expect(page.getByText('Delete Alert')).toBeVisible()
    await page.getByRole('button', { name: /confirm/i }).click()

    await expect(page.getByText(/alert deleted/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('cancels create modal without saving', async ({
    authenticatedPage: page,
  }) => {
    await page.getByRole('button', { name: /new alert/i }).click()
    await expect(page.getByText('Create Alert')).toBeVisible()
    await page.getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByText('Create Alert')).not.toBeVisible()
  })
})
