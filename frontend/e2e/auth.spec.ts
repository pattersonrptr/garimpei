import { CUSTOMER, SITE_BASE, test, expect, login } from './fixtures'

test.describe('Login', () => {
  test('shows the back-office login form', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByText('Garimpei').first()).toBeVisible()
    await expect(page.getByLabel('Username')).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Password' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
    // No sign-up here: it points users to the site instead
    await expect(page.getByRole('link', { name: 'Go to Garimpei' })).toHaveAttribute(
      'href',
      `${SITE_BASE}/entrar`,
    )
  })

  test('an administrator lands on the admin panel', async ({ page }) => {
    await login(page)
    await expect(page).toHaveURL(/\/admin$/)
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Username').fill('wrong_user')
    await page.getByRole('textbox', { name: 'Password' }).fill('wrong_pass')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await expect(page.getByText(/invalid username or password/i)).toBeVisible({
      timeout: 5000,
    })
  })

  test('shows validation message when fields are empty', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await expect(
      page.getByText(/please enter username and password/i),
    ).toBeVisible()
  })
})

test.describe('Logout', () => {
  test('logs out and redirects to login', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /logout/i }).click()
    // Confirmation dialog appears
    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page).toHaveURL(/\/login/)
  })
})

test.describe('Admins only (Phase 5e)', () => {
  test('a customer who signs in here is sent to the site', async ({ page }) => {
    expect(CUSTOMER.password, 'E2E_USER_PASSWORD is missing from .env').not.toBe('')
    await page.goto('/login')
    await page.getByLabel('Username').fill(CUSTOMER.username)
    await page.getByRole('textbox', { name: 'Password' }).fill(CUSTOMER.password)
    await page.getByRole('button', { name: 'Sign In' }).click()
    await expect(page).toHaveURL(new RegExp(`^${SITE_BASE}/(alertas|entrar)`))
  })

  test('the old sign-up address opens sign-up on the site', async ({ page }) => {
    await page.goto('/register')
    await expect(page).toHaveURL(`${SITE_BASE}/cadastro`)
  })

  test('the old "warn me" address keeps the book and price on the site', async ({ page }) => {
    await page.goto('/alertas/novo?isbn=9788535914849&condicao=usado&preco=20')
    await expect(page).toHaveURL(
      new RegExp(`^${SITE_BASE}/entrar\\?next=%2Falertas%2Fnovo%3Fisbn%3D9788535914849`),
    )
  })
})

test.describe('Auth guard', () => {
  test('unauthenticated user is redirected to login', async ({ page }) => {
    await page.goto('/admin/users')
    await expect(page).toHaveURL(/\/login\?next=%2Fadmin%2Fusers/)
  })

  test('authenticated user accessing /login is redirected to the admin panel', async ({
    page,
  }) => {
    await login(page)
    await page.goto('/login')
    await expect(page).toHaveURL(/\/admin$/)
  })
})
