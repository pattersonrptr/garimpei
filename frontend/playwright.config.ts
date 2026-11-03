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
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
})
