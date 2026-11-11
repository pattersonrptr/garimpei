import { describe, expect, it } from 'vitest'
import { safeNextPath, withNext } from '@/lib/nextPath'

describe('safeNextPath', () => {
  it('accepts paths inside the app', () => {
    expect(safeNextPath('/alertas/novo?isbn=9788535914849&condicao=usado')).toBe(
      '/alertas/novo?isbn=9788535914849&condicao=usado',
    )
  })

  it.each([
    null,
    '',
    'https://evil.example',
    '//evil.example/x',
    '/\\evil.example',
    'javascript:alert(1)',
    '/a\nb',
  ])('refuses %j', (raw) => {
    expect(safeNextPath(raw)).toBeNull()
  })
})

describe('withNext', () => {
  it('keeps the next path, encoded', () => {
    expect(withNext('/login', '/alertas/novo?isbn=1')).toBe(
      '/login?next=%2Falertas%2Fnovo%3Fisbn%3D1',
    )
  })

  it('drops an unsafe next path', () => {
    expect(withNext('/login', '//evil.example')).toBe('/login')
    expect(withNext('/login', null)).toBe('/login')
  })
})
