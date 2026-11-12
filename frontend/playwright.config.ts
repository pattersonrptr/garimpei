import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E configuration.
 *
 * By default tests run headless. To see the browser:
 *   npx playwright test --headed
 *
 * Or set the environment variable:
 *   HEADLESS=false npx playwright test
 */
const headless = process.env.HEADLESS !== 'false'
// Use an installed browser instead of Playwright's bundled one,
// e.g. E2E_CHANNEL=chrome npx playwright test --project=chromium
const channel = process.env.E2E_CHANNEL

// Screenshots and demo video for the READMEs (e2e/media/*.media.ts). Only
// added when asked for, so a plain `playwright test` never runs it:
//   MEDIA=1 E2E_CHANNEL=msedge npx playwright test --project=media
const media = {
  name: 'media',
  testMatch: /\.media\.ts$/,
  timeout: 120_000,
  use: {
    ...devices['Desktop Chrome'],
    ...(channel ? { channel } : {}),
    viewport: { width: 1366, height: 768 },
    locale: 'pt-BR',
    video: { mode: 'on' as const, size: { width: 1366, height: 768 } },
    launchOptions: { slowMo: 150 },
  },
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,

  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:80',
    // The UI follows the browser language; the specs assert English texts.
    locale: 'en-US',
    headless,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], ...(channel ? { channel } : {}) },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    ...(process.env.MEDIA ? [media] : []),
  ],
})
