/**
 * "Warn me" on the public site (Phase 5c/5e): the book page links to the
 * site's /alertas/novo with the book, the condition and a suggested price.
 * A visitor who is not signed in signs in and comes back to the same page,
 * creates the alert, sees it in "Meus alertas", and an offer already under
 * the price is e-mailed at once (local Mailpit).
 *
 * Runs against the Next.js site (E2E_SITE_URL, default :3000), not this app.
 * Uses a book from the dev catalog that has a used copy in stock.
 */

import { request } from '@playwright/test'
import { API_BASE, CUSTOMER, SITE_BASE, api, expect, mailpit, test } from './fixtures'

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

  test('signs in, comes back, creates the alert and gets the e-mail', async ({ page }) => {
    // The book page's "warn me" link stays on the site
    await page.goto(`${SITE_BASE}/livro/${book.isbn}`)
    const warnMe = page.getByRole('link', { name: /Me avise quando baixar/ }).first()
    await expect(warnMe).toHaveAttribute('href', /^\/alertas\/novo\?isbn=/)

    const link = `${SITE_BASE}/alertas/novo?isbn=${book.isbn}&condicao=usado&preco=13`
    await page.goto(link)

    // Not signed in: the sign-in page keeps where to come back to
    await expect(page).toHaveURL(/\/entrar\?next=%2Falertas%2Fnovo/)
    await expect(page.getByRole('link', { name: 'Criar conta' })).toHaveAttribute(
      'href',
      /\/cadastro\?next=%2Falertas%2Fnovo/,
    )
    await page.getByLabel('E-mail ou usuário').fill(CUSTOMER.username)
    await page.getByLabel('Senha').fill(CUSTOMER.password)
    await page.getByRole('button', { name: 'Entrar' }).click()

    // Back on the same page, filled in from the link
    await expect(page).toHaveURL(new RegExp(`/alertas/novo\\?isbn=${book.isbn}`))
    await expect(page.getByRole('heading', { name: 'Criar alerta' })).toBeVisible()
    await expect(page.getByText(book.title).first()).toBeVisible()
    await expect(page.getByLabel('Usado', { exact: true })).toBeChecked()
    await expect(page.locator('input[name=price]')).toHaveValue('13,00')

    // A price above today's lowest used copy: the e-mail goes out at once
    const price = Math.ceil(book.lowestUsed) + 5
    await page.locator('input[name=price]').fill(String(price))
    await page.getByRole('button', { name: 'Criar alerta' }).click()

    await expect(page).toHaveURL(/\/alertas\?criado=1$/)
    const card = page.locator('.alert-card', { hasText: book.title })
    await expect(card).toContainText('Livro · Usado')
    await expect(card).toContainText('abaixo do seu alvo')
    await expect.poll(async () => (await mailpit.search(book.title)).length).toBeGreaterThan(0)

    // The same link again: one alert per book and condition
    await page.goto(link)
    await page.getByRole('button', { name: 'Criar alerta' }).click()
    await expect(page.getByText(/Você já tem um alerta para este produto/)).toBeVisible()
  })
})
