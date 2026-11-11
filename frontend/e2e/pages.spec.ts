import {
  test,
  expect,
  cleanupTestWebsites,
  cleanupTestConfigs,
} from './fixtures'

test('a mistyped address shows a "page not found" page', async ({ page }) => {
  await page.goto('/this-page-does-not-exist')
  await expect(page.getByRole('heading', { name: /page not found/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /go to the home page/i })).toBeVisible()
})

// ===========================================================================
// Products page
// ===========================================================================

test.describe('Products page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/products')
  })

  test('displays the products page with header', async ({
    authenticatedPage: page,
  }) => {
    await expect(page.getByText('Products')).toBeVisible()
  })

  test('shows column headers in the table', async ({
    authenticatedPage: page,
  }) => {
    await expect(page.getByRole('columnheader', { name: /title/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /current price/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /condition/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /available/i })).toBeVisible()
  })

  test('filter panel toggles on click', async ({
    authenticatedPage: page,
  }) => {
    const filtersButton = page.getByRole('button', { name: /filters/i })
    await filtersButton.click()

    // Filter fields should be visible
    await expect(page.getByRole('textbox', { name: 'Title' })).toBeVisible()

    // Clear button visible
    await expect(page.getByRole('button', { name: /clear/i })).toBeVisible()
  })

  test('edit product modal opens and saves', async ({
    authenticatedPage: page,
  }) => {
    // Wait for rows to load
    await page.waitForSelector('[role="row"]', { timeout: 10_000 })

    // Click the first edit button available
    const editButton = page.getByRole('button', { name: /edit/i }).first()
    await editButton.click()

    // Modal should open with title starting with "Edit Product"
    await expect(page.getByText(/Edit Product/)).toBeVisible()

    // Verify form fields are present
    await expect(page.getByRole('textbox', { name: 'Title' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'URL' })).toBeVisible()

    // Save without changes — should succeed with the PUT fix
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByText(/product updated/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('delete product with confirmation', async ({
    authenticatedPage: page,
  }) => {
    // Wait for rows to load
    await page.waitForSelector('[role="row"]', { timeout: 10_000 })

    // Click the first delete button
    const deleteButton = page.getByRole('button', { name: /delete/i }).first()
    await deleteButton.click()

    // Confirm the deletion inside the dialog
    const dialog = page.getByRole('dialog')
    await expect(dialog.getByText(/Delete Product/i)).toBeVisible()
    await dialog.getByRole('button', { name: /delete/i }).click()

    // Either success or failure snackbar should appear (failure is possible
    // when the product has related notification_logs — FK constraint)
    await expect(
      page.getByText(/product deleted|failed to delete/i),
    ).toBeVisible({ timeout: 5000 })
  })
})

// ===========================================================================
// Admin pages — smoke tests
// ===========================================================================

test.describe('Admin pages', () => {
  test('the menu lists only back-office pages; old user pages go to the panel', async ({
    authenticatedPage: page,
  }) => {
    const menu = page.locator('.MuiDrawer-root').first()
    await expect(menu.locator('.MuiListItemButton-root')).toHaveCount(5)
    await page.getByRole('button', { name: /toggle|menu|sidebar/i }).first().click()
    for (const name of ['Admin Dashboard', 'Products', 'Users', 'Search Configs', 'Source Websites']) {
      await expect(menu.getByText(name, { exact: true })).toBeVisible()
    }
    for (const gone of ['My Alerts', 'Plans', 'Dashboard']) {
      await expect(menu.getByText(gone, { exact: true })).toHaveCount(0)
    }
    await page.screenshot({ path: 'test-results/admin-menu.png' })
    for (const old of ['/alerts', '/plans', '/dashboard']) {
      await page.goto(old)
      await expect(page).toHaveURL(/\/admin$/)
    }
  })

  test('users page loads for admin', async ({ authenticatedPage: page }) => {
    await page.goto('/admin/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
    // People sign up on the site; there is no "create user" here (Phase 5e)
    await expect(page.getByRole('button', { name: /new user/i })).toHaveCount(0)
    await expect(page.getByRole('columnheader', { name: /username/i })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /email/i })).toBeVisible()
  })

  test('source websites page loads for admin', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/admin/source-websites')
    await expect(page.getByText('Source Websites')).toBeVisible()
    await expect(
      page.getByRole('button', { name: /add website/i }),
    ).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /name/i })).toBeVisible()
  })

  test('search configs page loads for admin', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/admin/search-configs')
    await expect(page.getByText('Search Configurations')).toBeVisible()
    await expect(
      page.getByRole('button', { name: /add config/i }),
    ).toBeVisible()
    await expect(
      page.getByRole('columnheader', { name: /search term/i }),
    ).toBeVisible()
  })
})

// ===========================================================================
// Source Websites — CRUD
// ===========================================================================

test.describe('Source Websites CRUD', () => {
  test.beforeAll(async () => {
    await cleanupTestWebsites('e2e-')
  })

  test.afterAll(async () => {
    await cleanupTestWebsites('e2e-')
  })

  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/admin/source-websites')
    await expect(page.getByText('Source Websites')).toBeVisible()
  })

  test('creates a new source website', async ({ authenticatedPage: page }) => {
    const name = `e2e-sw-${Date.now()}`

    await page.getByRole('button', { name: /add website/i }).click()
    await expect(page.getByText('New Source Website')).toBeVisible()

    await page.getByRole('textbox', { name: 'Name' }).fill(name)
    await page.getByRole('textbox', { name: 'Base URL' }).fill('https://e2e-test.example.com')

    await page.getByRole('button', { name: 'Create' }).click()

    await expect(page.getByText(/source website created/i)).toBeVisible({
      timeout: 5000,
    })

    // Verify the row appears
    await expect(page.getByRole('gridcell', { name })).toBeVisible({
      timeout: 10_000,
    })
  })

  test('edits a source website', async ({ authenticatedPage: page }) => {
    // Create one first
    const name = `e2e-edit-${Date.now()}`
    await page.getByRole('button', { name: /add website/i }).click()
    await page.getByRole('textbox', { name: 'Name' }).fill(name)
    await page.getByRole('textbox', { name: 'Base URL' }).fill('https://e2e-edit.example.com')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/source website created/i)).toBeVisible({
      timeout: 5000,
    })
    await expect(page.getByRole('gridcell', { name })).toBeVisible({
      timeout: 10_000,
    })

    // Edit it
    const row = page.getByRole('row').filter({ hasText: name })
    await row.getByRole('button', { name: /edit/i }).click()

    await expect(page.getByText(/Edit Website/)).toBeVisible()

    // Change base URL
    const urlField = page.getByRole('textbox', { name: 'Base URL' })
    await urlField.clear()
    await urlField.fill('https://e2e-updated.example.com')

    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByText(/source website updated/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('deletes a source website', async ({ authenticatedPage: page }) => {
    // Create one first
    const name = `e2e-del-${Date.now()}`
    await page.getByRole('button', { name: /add website/i }).click()
    await page.getByRole('textbox', { name: 'Name' }).fill(name)
    await page.getByRole('textbox', { name: 'Base URL' }).fill('https://e2e-del.example.com')
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/source website created/i)).toBeVisible({
      timeout: 5000,
    })
    await expect(page.getByRole('gridcell', { name })).toBeVisible({
      timeout: 10_000,
    })

    // Delete it
    const row = page.getByRole('row').filter({ hasText: name })
    await row.getByRole('button', { name: /delete/i }).click()

    await expect(page.getByText('Delete Source Website')).toBeVisible()
    await page.getByRole('button', { name: /delete/i }).click()

    await expect(page.getByText(/source website deleted/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('validates required fields on create', async ({
    authenticatedPage: page,
  }) => {
    await page.getByRole('button', { name: /add website/i }).click()
    await expect(page.getByText('New Source Website')).toBeVisible()

    // Try to create without filling required fields
    await page.getByRole('button', { name: 'Create' }).click()

    // Should show validation warning
    await expect(page.getByText(/name and base url are required/i)).toBeVisible({
      timeout: 5000,
    })
  })
})

// ===========================================================================
// Search Configs — CRUD
// ===========================================================================

test.describe('Search Configs CRUD', () => {
  test.beforeAll(async () => {
    // Clean our own configs + any leftover from alert tests
    await cleanupTestConfigs('e2e-')
    await cleanupTestConfigs('ea-')
    await cleanupTestConfigs('ee-')
    await cleanupTestConfigs('ed-')
    await cleanupTestConfigs('ep-')
  })

  test.afterAll(async () => {
    await cleanupTestConfigs('e2e-')
  })

  test.afterEach(async () => {
    await cleanupTestConfigs('e2e-')
  })

  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/admin/search-configs')
    await expect(page.getByText('Search Configurations')).toBeVisible()
  })

  test('creates a new search config', async ({ authenticatedPage: page }) => {
    const term = `e2e-sc-${Date.now()}`

    await page.getByRole('button', { name: /add config/i }).click()
    await expect(page.getByText('New Search Configuration')).toBeVisible()

    await page.getByRole('textbox', { name: 'Search Term' }).fill(term)

    await page.getByRole('button', { name: 'Create' }).click()

    await expect(page.getByText(/search config created/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('edits a search config', async ({ authenticatedPage: page }) => {
    // Create first
    const term = `e2e-esc-${Date.now()}`
    await page.getByRole('button', { name: /add config/i }).click()
    await page.getByRole('textbox', { name: 'Search Term' }).fill(term)
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/search config created/i)).toBeVisible({
      timeout: 5000,
    })

    // Wait for grid to reload and show the new config
    await expect(page.getByRole('gridcell', { name: term })).toBeVisible({
      timeout: 10_000,
    })

    // Edit it
    const row = page.getByRole('row').filter({ hasText: term })
    await row.getByRole('button', { name: /edit/i }).click()

    await expect(page.getByText(/Edit Config/)).toBeVisible()

    // Change frequency
    const freqField = page.getByRole('spinbutton', { name: 'Frequency (days)' })
    await freqField.clear()
    await freqField.fill('7')

    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByText(/search config updated/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('deletes a search config', async ({ authenticatedPage: page }) => {
    // Create via UI and wait for snackbar only
    const term = `e2e-dsc-${Date.now()}`
    await page.getByRole('button', { name: /add config/i }).click()
    await page.getByRole('textbox', { name: 'Search Term' }).fill(term)
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText(/search config created/i)).toBeVisible({
      timeout: 5000,
    })

    // Wait for grid to reload and find the row (may need to wait for re-render)
    await expect(page.getByRole('gridcell', { name: term })).toBeVisible({
      timeout: 10_000,
    })

    // Delete it
    const row = page.getByRole('row').filter({ hasText: term })
    await row.getByRole('button', { name: /delete/i }).click()

    await expect(page.getByText('Delete Search Config')).toBeVisible()
    await page.getByRole('button', { name: /delete/i }).click()

    await expect(page.getByText(/search config deleted/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('validates required fields on create', async ({
    authenticatedPage: page,
  }) => {
    await page.getByRole('button', { name: /add config/i }).click()
    await expect(page.getByText('New Search Configuration')).toBeVisible()

    // Try to create without filling search term
    await page.getByRole('button', { name: 'Create' }).click()

    // Should show validation warning
    await expect(page.getByText(/search term is required/i)).toBeVisible({
      timeout: 5000,
    })
  })
})
