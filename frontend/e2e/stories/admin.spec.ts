/**
 * Administrator stories. Letters point to docs/qa/exploratory-report.md.
 */

import { PRODUCT_PREFIX, TERM_PREFIX, api, expect, test } from '../fixtures'

test.describe('Administrator stories', () => {
  test.beforeEach(async () => {
    await api.reset()
  })

  test.afterAll(async () => {
    await api.reset()
  })

  test('A: deleting a search still used by an alert explains why it cannot go', async ({
    authenticatedPage: page,
  }) => {
    const term = `${TERM_PREFIX} in use`
    await api.createCustomerAlert(term, 50)

    await page.goto('/admin/search-configs')
    await page.getByRole('searchbox', { name: /search/i }).fill(term)
    const row = page.getByRole('row').filter({ hasText: term })
    await row.getByRole('button', { name: 'Delete' }).click()
    await page.getByRole('dialog').getByRole('button', { name: /confirm|delete/i }).click()

    await expect(page.getByText(/used by 1 alert/i)).toBeVisible()
    await expect(row).toBeVisible()
  })

  test('G: "select all" offers to delete the whole page of products', async ({
    authenticatedPage: page,
  }) => {
    await api.seedProduct(`${PRODUCT_PREFIX} bulk one`, 10)
    await api.seedProduct(`${PRODUCT_PREFIX} bulk two`, 20)

    await page.goto('/products')
    await page.getByRole('button', { name: 'Filters' }).click()
    await page.getByRole('textbox', { name: 'Title' }).fill(`${PRODUCT_PREFIX} bulk`)
    await expect(page.getByText(/1–2 of 2/)).toBeVisible()

    await page.getByRole('checkbox', { name: /select all rows/i }).check()
    await page.getByRole('button', { name: /delete selected \(2\)/i }).click()
    await page.getByRole('dialog').getByRole('button', { name: /confirm|delete/i }).click()
    await expect(page.getByText(/2 products deleted/i)).toBeVisible()
  })

  test('G: "select all" offers bulk actions on the users page too', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/admin/users')
    await expect(page.getByRole('grid')).toBeVisible()
    await page.getByRole('checkbox', { name: /select all rows/i }).check()
    await expect(page.getByRole('button', { name: /delete selected/i }).or(page.getByText(/delete selected/i))).toBeVisible()
  })
})
