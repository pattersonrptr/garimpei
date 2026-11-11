import { describe, expect, it } from 'vitest'
import { siteUrl } from '@/lib/site'

describe('siteUrl', () => {
  it('joins the site address and a path', () => {
    expect(siteUrl('/alertas', 'https://garimpei.com.br/')).toBe('https://garimpei.com.br/alertas')
    expect(siteUrl('cadastro', 'https://garimpei.com.br')).toBe('https://garimpei.com.br/cadastro')
  })

  it('keeps the query string', () => {
    expect(siteUrl('/alertas/novo?isbn=978&condicao=usado', 'http://localhost:3000')).toBe(
      'http://localhost:3000/alertas/novo?isbn=978&condicao=usado',
    )
  })

  it('defaults to the local site', () => {
    expect(siteUrl()).toMatch(/^http:\/\/localhost:3000\/$|^https?:\/\/.+\/$/)
  })
})
