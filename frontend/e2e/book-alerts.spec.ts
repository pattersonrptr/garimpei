/**
 * "Warn me" (Phase 4d): the public book page links to /alertas/novo with the
 * book, the condition and a suggested price. A visitor who is not logged in
 * logs in and comes back to the same page, creates the alert, and an offer
 * already under the price is e-mailed at once (local Mailpit).
 *
 * Uses a book from the dev catalog that has a used copy in stock.
 */

import { request } from '@playwright/test'
import { API_BASE, CUSTOMER, api, expect, mailpit, test } from './fixtures'

type BookItem = { id: string; attributes: { title: string; lowest_used: number | null } }

async function bookWithUsedCopy(): Promise<{ isbn: string; title: string; lowestUsed: number }> {
  const ctx = await request.newContext()
  const resp = await ctx.get(`${API_BASE}/books/index?limit=50`)
  const books = ((await resp.json()).data ?? []) as BookItem[]
  await ctx.dispose()
  const book = books.find((b) => b.attributes.lowest_used != null)
  if (!book) throw new Error('The dev catalog has no book with a used copy in stock')
  return { isbn: book.id, title: book.attributes.title, lowestUsed: book.attributes.lowest_used! }
}

test.describe('Book alert from the public page', () => {
  let book: Awaited<ReturnType<typeof bookWithUsedCopy>>

  test.beforeAll(async () => {
    book = await bookWithUsedCopy()
  })

  test.beforeEach(async () => {
    await api.reset()
    await mailpit.clear(book.title)
  })

  test.afterAll(async () => {
    await api.reset()
    await mailpit.clear(book.title)
  })

  test('logs in, comes back, creates the alert and gets the e-mail', async ({ page }) => {
    const link = `/alertas/novo?isbn=${book.isbn}&condicao=usado&preco=13`
    await page.goto(link)

    // Not logged in: the login page keeps where to come back to
    await expect(page).toHaveURL(/\/login\?next=%2Falertas%2Fnovo/)
    await expect(page.getByRole('link', { name: /sign up|register|create/i })).toHaveAttribute(
      'href',
      /\/register\?next=%2Falertas%2Fnovo/,
    )
    await page.getByLabel('Username').fill(CUSTOMER.username)
    await page.getByRole('textbox', { name: 'Password' }).fill(CUSTOMER.password)
    await page.getByRole('button', { name: 'Sign In' }).click()

    // Back on the same page, filled in from the link
    await expect(page).toHaveURL(new RegExp(`/alertas/novo\\?isbn=${book.isbn}`))
    await expect(page.getByText('Warn me when it drops')).toBeVisible()
    await expect(page.getByText(book.title)).toBeVisible()
    await expect(page.getByLabel('Max Price', { exact: false })).toHaveValue('13.00')

    // A price above today's lowest used copy: the e-mail goes out at once
    const price = Math.ceil(book.lowestUsed) + 5
    await page.getByLabel('Max Price', { exact: false }).fill(String(price))
    await page.getByRole('button', { name: 'Create alert' }).click()

    await expect(page).toHaveURL(/\/alerts$/)
    await expect(page.getByText('Book · Used')).toBeVisible()
    await expect.poll(async () => (await mailpit.search(book.title)).length).toBeGreaterThan(0)

    // The same link again: one alert per book and condition
    await page.goto(link)
    await page.getByRole('button', { name: 'Create alert' }).click()
    await expect(page.getByText(/already have an alert for this book/)).toBeVisible()
  })
})
