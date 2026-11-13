// Mobile and desktop screenshots of site pages (used by the e2e-local skill).
//
// Run from frontend/, so Playwright resolves from its node_modules:
//   node ../.claude/skills/e2e-local/screenshots.mjs [--login] <out-dir> <path>...
//
// --login signs in on the site as E2E_USER_USERNAME (from the environment or
// the repository .env) before taking the screenshots.

import { existsSync, mkdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { join, resolve } from 'node:path'

const require = createRequire(join(process.cwd(), 'package.json'))
const { chromium } = require('@playwright/test')

const SIZES = {
  mobile: { width: 390, height: 844 },
  desktop: { width: 1366, height: 900 },
}

function dotEnv() {
  const file = resolve(process.cwd(), '..', '.env')
  if (!existsSync(file)) return {}
  const values = {}
  for (const line of readFileSync(file, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/)
    if (match) values[match[1]] = match[2].replace(/^["']|["']$/g, '')
  }
  return values
}

function slug(path) {
  return path.replace(/^\//, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/-$/, '') || 'home'
}

async function signIn(page, site, env, outDir) {
  try {
    await submitSignIn(page, site, env)
  } catch (error) {
    const file = join(outDir, 'signin-failed.png')
    await page.screenshot({ path: file, fullPage: true }).catch(() => {})
    const shown = await page.locator('.form-error').allInnerTexts().catch(() => [])
    throw new Error(`sign-in failed (${shown.join(' ') || error.message}); see ${file}`)
  }
}

async function submitSignIn(page, site, env) {
  const login = process.env.E2E_USER_USERNAME ?? env.E2E_USER_USERNAME
  const password = process.env.E2E_USER_PASSWORD ?? env.E2E_USER_PASSWORD
  if (!login || !password) throw new Error('E2E_USER_USERNAME/PASSWORD not set')
  await page.goto(`${site}/entrar`)
  await page.fill('input[name=login]', login)
  await page.fill('input[name=password]', password)
  await Promise.all([
    page.waitForURL((url) => !url.pathname.startsWith('/entrar')),
    // the top bar has its own submit button (Buscar): stay inside the form
    page.click('form:has(input[name=login]) button[type=submit]'),
  ])
}

async function main() {
  const args = process.argv.slice(2)
  const login = args[0] === '--login'
  if (login) args.shift()
  const [outDir, ...paths] = args
  if (!outDir || paths.length === 0) {
    console.error('usage: screenshots.mjs [--login] <out-dir> <path>...')
    process.exit(2)
  }
  mkdirSync(outDir, { recursive: true })
  const env = dotEnv()
  const site = process.env.E2E_SITE_URL ?? env.E2E_SITE_URL ?? 'http://localhost:3000'
  const browser = await chromium.launch({ channel: process.env.E2E_CHANNEL || undefined })
  try {
    for (const [size, viewport] of Object.entries(SIZES)) {
      const context = await browser.newContext({ viewport, locale: 'pt-BR' })
      const page = await context.newPage()
      if (login) await signIn(page, site, env, outDir)
      for (const path of paths) {
        await page.goto(`${site}${path}`, { waitUntil: 'networkidle' })
        const file = join(outDir, `${slug(path)}-${size}.png`)
        await page.screenshot({ path: file, fullPage: true })
        console.log(file)
      }
      await context.close()
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
