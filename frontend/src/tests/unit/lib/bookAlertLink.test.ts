import { describe, expect, it } from 'vitest'
import { conditionFromLink, parsePrice, priceFromLink } from '@/lib/bookAlertLink'

describe('conditionFromLink', () => {
  it('reads the Portuguese words of the public site', () => {
    expect(conditionFromLink('usado')).toBe('used')
    expect(conditionFromLink('novo')).toBe('new')
    expect(conditionFromLink('qualquer')).toBe('any')
  })

  it('falls back to any', () => {
    expect(conditionFromLink(null)).toBe('any')
    expect(conditionFromLink('seminovo')).toBe('any')
  })
})

describe('priceFromLink', () => {
  it('shows two decimals', () => {
    expect(priceFromLink('25.9')).toBe('25.90')
  })

  it('is empty when missing or invalid', () => {
    expect(priceFromLink(null)).toBe('')
    expect(priceFromLink('abc')).toBe('')
    expect(priceFromLink('-3')).toBe('')
    expect(priceFromLink('0')).toBe('')
  })
})

describe('parsePrice', () => {
  it('accepts a comma or a dot', () => {
    expect(parsePrice('25,90')).toBe(25.9)
    expect(parsePrice(' 25.90 ')).toBe(25.9)
  })

  it('is NaN for empty, zero or text', () => {
    expect(parsePrice('')).toBeNaN()
    expect(parsePrice('0')).toBeNaN()
    expect(parsePrice('vinte')).toBeNaN()
  })
})
