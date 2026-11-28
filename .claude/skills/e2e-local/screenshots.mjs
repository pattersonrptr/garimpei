// Mobile and desktop screenshots of site or admin pages (used by the
// e2e-local skill).
//
// Run from frontend/, so Playwright resolves from its node_modules:
//   node ../.claude/skills/e2e-local/screenshots.mjs [--login | --admin]
//        [--action <file.mjs>] <out-dir> <path>...
//
// --login signs in on the site as E2E_USER_USERNAME (from the environment or
// the repository .env) before taking the screenshots.
// --admin signs in on the back office (E2E_BASE_URL, default
// http://localhost) as E2E_ADMIN_USERNAME; the paths are admin paths.
// --action loads a module whose default export runs on each page before the
// screenshot: `export default async (page, { size, path }) => { ... }`.
// The action's file name goes into the PNG names (admin-users-refused-mobile.png).

import { existsSync, mkdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { basename, join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const require = createRequire(join(process.cwd(), 'package.json'))
const { chromium } = require('@playwright/test')

const SIZES = {
  mobile: { width: 390, height: 844 },
  desktop: { width: 1366, height: 900 },
}

const USAGE =
  'usage: screenshots.mjs [--login | --admin] [--action <file.mjs>] <out-dir> <path>...'

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

function setting(env, name, fallback) {
  return process.env[name] ?? env[name] ?? fallback
}

async function signIn(page, outDir, submit) {
  try {
    await submit()
  } catch (error) {
    const file = join(outDir, 'signin-failed.png')
    await page.screenshot({ path: file, fullPage: true }).catch(() => {})
    const shown = await page.locator('.form-error').allInnerTexts().catch(() => [])
    throw new Error(`sign-in failed (${shown.join(' ') || error.message}); see ${file}`)
  }
}

async function submitSiteSignIn(page, base, env) {
  const login = setting(env, 'E2E_USER_USERNAME')
  const password = setting(env, 'E2E_USER_PASSWORD')
  if (!login || !password) throw new Error('E2E_USER_USERNAME/PASSWORD not set')
  await page.goto(`${base}/entrar`)
  await page.fill('input[name=login]', login)
  await page.fill('input[name=password]', password)
  await Promise.all([
    page.waitForURL((url) => !url.pathname.startsWith('/entrar')),
    // the top bar has its own submit button (Buscar): stay inside the form
    page.click('form:has(input[name=login]) button[type=submit]'),
  ])
}

async function submitAdminSignIn(page, base, env) {
  const login = setting(env, 'E2E_ADMIN_USERNAME')
  const password = setting(env, 'E2E_ADMIN_PASSWORD')
  if (!login || !password) throw new Error('E2E_ADMIN_USERNAME/PASSWORD not set')
  await page.goto(`${base}/login`)
  await page.locator('input:not([type=password])').first().fill(login)
  await page.locator('input[type=password]').fill(password)
  await Promise.all([
    page.waitForURL(/\/admin$/),
    page.locator('button[type=submit]').click(),
  ])
}

function parseArgs(argv) {
  const options = { mode: 'site', action: null, outDir: null, paths: [] }
  const args = [...argv]
  while (args[0]?.startsWith('--')) {
    const flag = args.shift()
    if (flag === '--login') options.mode = 'login'
    else if (flag === '--admin') options.mode = 'admin'
    else if (flag === '--action' && args[0]) options.action = args.shift()
    else throw new Error(`bad option ${flag}\n${USAGE}`)
  }
  ;[options.outDir, ...options.paths] = args
  if (!options.outDir || options.paths.length === 0) throw new Error(USAGE)
  return options
}

async function main() {
  let options
  try {
    options = parseArgs(process.argv.slice(2))
  } catch (error) {
    console.error(error.message)
    process.exit(2)
  }
  const { mode, outDir, paths } = options
  mkdirSync(outDir, { recursive: true })
  const env = dotEnv()
  const base =
    mode === 'admin'
      ? setting(env, 'E2E_BASE_URL', 'http://localhost')
      : setting(env, 'E2E_SITE_URL', 'http://localhost:3000')
  const action = options.action
    ? (await import(pathToFileURL(resolve(options.action)).href)).default
    : null
  const suffix = options.action ? `-${basename(options.action).replace(/\.[^.]+$/, '')}` : ''

  const browser = await chromium.launch({ channel: process.env.E2E_CHANNEL || undefined })
  try {
    for (const [size, viewport] of Object.entries(SIZES)) {
      const context = await browser.newContext({ viewport, locale: 'pt-BR' })
      const page = await context.newPage()
      if (mode === 'login') await signIn(page, outDir, () => submitSiteSignIn(page, base, env))
      if (mode === 'admin') await signIn(page, outDir, () => submitAdminSignIn(page, base, env))
      for (const path of paths) {
        await page.goto(`${base}${path}`, { waitUntil: 'networkidle' })
        if (action) await action(page, { size, path })
        const file = join(outDir, `${slug(path)}${suffix}-${size}.png`)
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
