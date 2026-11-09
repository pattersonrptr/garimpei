import { ADMIN_USER, TERM_PREFIX, api, expect, test } from './fixtures'

test.describe('Dashboard', () => {
  // The cards show for someone who already has alerts; a brand-new account
  // gets the onboarding screen instead. The alert is paused so it does not
  // take one of the plan's active-alert slots the other specs use.
  test.beforeAll(async () => {
    await api.reset()
    await api.createAlert(`${TERM_PREFIX} dashboard`, 100, ['estante_virtual'], ADMIN_USER, false)
  })

  test.afterAll(async () => {
    await api.reset()
  })

  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/dashboard')
  })

  test('displays the three dashboard cards', async ({
    authenticatedPage: page,
  }) => {
    await expect(page.getByRole('heading', { name: 'Active Alerts' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Recent Opportunities' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Next Checks' })).toBeVisible()
  })

  test('active alerts card shows count', async ({
    authenticatedPage: page,
  }) => {
    const card = page.locator('div').filter({ hasText: /^Active Alerts/ }).first()
    await expect(card).toBeVisible()
    // Should have a "total alert(s) configured" subtext
    await expect(page.getByText(/total alert\(?s?\)? configured/i)).toBeVisible()
  })

  test('clicking active alerts card navigates to alerts page', async ({
    authenticatedPage: page,
  }) => {
    // The Active Alerts card is clickable and navigates to /alerts
    const card = page.locator('[class*="MuiCard"]').filter({ hasText: 'Active Alerts' }).first()
    await card.click()
    await expect(page).toHaveURL(/\/alerts/)
  })
})
