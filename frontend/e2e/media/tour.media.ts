/**
 * Screenshots and demo video of the public site, for the READMEs.
 *
 * Not a test suite: it walks the main journey on the local stack and saves
 * what a reader of the README should see. Run it again when the site's look
 * changes (from frontend/):
 *
 *   MEDIA=1 npx playwright test --project=media
 *
 * Writes PNGs to docs/screenshots/ and the video to docs/demo/ (override with
 * MEDIA_SCREENSHOTS / MEDIA_DEMO; pick the book with MEDIA_ISBN). Uses the
 * E2E customer account from .env and cleans up its alerts and e-mails before
 * and after.
 */

import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { request, type Page } from '@playwright/test'
import {
  API_BASE,
  CUSTOMER,
  MAILPIT_BASE,
  SITE_BASE,
  api,
  expect,
  mailpit,
  test,
} from '../fixtures'

const SHOTS = path.resolve(process.env.MEDIA_SCREENSHOTS ?? '../docs/screenshots')
const DEMO = path.resolve(process.env.MEDIA_DEMO ?? '../docs/demo')

type BookAttributes = {
  title: string
  lowest_used: number | null
}
type Book = { isbn: string; title: string; lowestUsed: number; query: string }

/**
 * The book shown in the media: MEDIA_ISBN, or by default one with a cover, new
 * and used offers in three stores and a used copy well below the new one.
 */
const ISBN = process.env.MEDIA_ISBN ?? '9788525433206'

async function showcaseBook(): Promise<Book> {
  const ctx = await request.newContext()
  const resp = await ctx.get(`${API_BASE}/books/${ISBN}`)
  if (!resp.ok()) throw new Error(`Book ${ISBN} is not in the dev catalog; set MEDIA_ISBN`)
  const attributes = (await resp.json()).data.attributes as BookAttributes
  await ctx.dispose()
  if (attributes.lowest_used == null) throw new Error(`Book ${ISBN} has no used copy in stock`)
  const title = attributes.title
  return {
    isbn: ISBN,
    title,
    lowestUsed: attributes.lowest_used,
    query: title.split(/\s+/).filter((w) => w.length > 3)[0] ?? title,
  }
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(SHOTS, { recursive: true })
  // Wait for the covers: a half-loaded image looks broken in a README
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => Array.from(document.images).every((img) => img.complete))
  await page.screenshot({
    path: path.join(SHOTS, `${name}.png`),
    fullPage: true,
  })
}

/**
 * Playwright's raw video is about 1.4 MB; VP9 with ffmpeg brings it to ~0.4 MB
 * with no visible loss. Without ffmpeg on PATH the raw file is kept.
 */
async function saveDemo(raw: string) {
  fs.mkdirSync(DEMO, { recursive: true })
  const out = path.join(DEMO, 'garimpei-demo.webm')
  const args = ['-v', 'error', '-y', '-i', raw, '-c:v', 'libvpx-vp9', '-crf', '42', '-b:v', '0']
  const ffmpeg = spawnSync('ffmpeg', [...args, '-row-mt', '1', '-an', out])
  if (ffmpeg.status !== 0) {
    console.warn('ffmpeg not available or failed: saving the uncompressed video')
    fs.copyFileSync(raw, out)
  }
}

/** A short pause so the video is watchable. */
const linger = (page: Page, ms = 1200) => page.waitForTimeout(ms)

async function signIn(page: Page) {
  await page.getByLabel('E-mail ou usuário').fill(CUSTOMER.username)
  await page.getByLabel('Senha').fill(CUSTOMER.password)
  await page.locator('form:has(input[name=login])').getByRole('button', { name: 'Entrar' }).click()
}

let book: Book

test.beforeAll(async () => {
  book = await showcaseBook()
})

test.beforeEach(async () => {
  await api.reset()
  await mailpit.clear(book.title)
})

test.afterAll(async () => {
  await api.reset()
  await mailpit.clear(book.title)
})

test('desktop journey: search, compare, warn me, e-mail (with video)', async ({ page }) => {
  // 1. Home and search
  await page.goto(`${SITE_BASE}/`)
  await linger(page)
  await shot(page, 'site-home-desktop')

  await page.getByRole('searchbox').first().fill(book.query)
  await linger(page, 600)
  await page.getByRole('searchbox').first().press('Enter')
  await expect(page).toHaveURL(/\/busca\?q=/)
  await expect(page.getByText(book.title).first()).toBeVisible()
  await linger(page)
  await shot(page, 'site-search-desktop')

  // 2. The book page: new and used side by side
  await page.getByRole('link', { name: book.title }).first().click()
  await expect(page.getByRole('heading', { level: 1, name: book.title })).toBeVisible()
  await linger(page, 2000)
  await shot(page, 'site-book-page-desktop')
  await page.mouse.wheel(0, 700)
  await linger(page, 1500)

  // 3. "Me avise": sign in, come back to the filled-in form
  await page
    .getByRole('link', { name: /Me avise quando baixar/ })
    .first()
    .click()
  await expect(page).toHaveURL(/\/entrar\?next=/)
  await linger(page)
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Criar alerta' })).toBeVisible()

  // A target above today's lowest used copy, so the e-mail goes out at once
  await page.locator('input[name=price]').fill(String(Math.ceil(book.lowestUsed) + 5))
  await linger(page)
  await shot(page, 'site-alert-form-desktop')
  await page.getByRole('button', { name: 'Criar alerta' }).click()

  // 4. "Meus alertas"
  await expect(page).toHaveURL(/\/alertas\?criado=1$/)
  await expect(page.locator('.alert-card', { hasText: book.title })).toBeVisible()
  await linger(page, 2000)
  await shot(page, 'site-my-alerts-desktop')

  // 5. The e-mail as the user sees it (its HTML, served by the local Mailpit)
  await expect.poll(async () => (await mailpit.search(book.title)).length).toBeGreaterThan(0)
  const [mail] = await mailpit.search(book.title)
  await page.goto(`${MAILPIT_BASE}/view/${mail.ID}.html`)
  await expect(page.getByText(book.title).first()).toBeVisible()
  await linger(page, 2500)
  await shot(page, 'site-alert-email-desktop')

  // Save the video under a stable name, compressed (pre-commit refuses files over 1 MB)
  const video = page.video()
  await page.close()
  if (video) await saveDemo(await video.path())
})

test.describe('mobile', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('mobile screenshots', async ({ page }) => {
    await page.goto(`${SITE_BASE}/`)
    await shot(page, 'site-home-mobile')

    await page.goto(`${SITE_BASE}/busca?q=${encodeURIComponent(book.query)}`)
    await expect(page.getByText(book.title).first()).toBeVisible()
    await shot(page, 'site-search-mobile')

    await page.goto(`${SITE_BASE}/livro/${book.isbn}`)
    await expect(page.getByRole('heading', { level: 1, name: book.title })).toBeVisible()
    await shot(page, 'site-book-page-mobile')

    // "Meus alertas" with one alert, created through the site's form
    const price = Math.ceil(book.lowestUsed) + 5
    await page.goto(`${SITE_BASE}/alertas/novo?isbn=${book.isbn}&condicao=usado&preco=${price}`)
    await signIn(page)
    await expect(page.getByRole('heading', { name: 'Criar alerta' })).toBeVisible()
    await page.getByRole('button', { name: 'Criar alerta' }).click()
    await expect(page).toHaveURL(/\/alertas\?criado=1$/)
    await expect(page.locator('.alert-card', { hasText: book.title })).toBeVisible()
    await shot(page, 'site-my-alerts-mobile')
  })
})
