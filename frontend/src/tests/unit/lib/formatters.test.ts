/**
 * Tests for lib/formatters.ts
 */

import { beforeAll, describe, expect, it } from 'vitest'
import i18n from '@/i18n'
import {
  formatChartDateLabel,
  formatCurrency,
  formatDate,
  formatDateTime,
} from '@/lib/formatters'

// These expectations are for the pt-BR formats (the unit tests default to en)
beforeAll(async () => {
  await i18n.changeLanguage('pt-BR')
})

describe('formatCurrency', () => {
  it('formats a number as BRL currency', () => {
    expect(formatCurrency(1234.56)).toContain('1.234,56')
  })

  it('formats zero correctly', () => {
    expect(formatCurrency(0)).toContain('0,00')
  })
})

describe('formatDate', () => {
  it('returns a date string in dd/mm/yyyy format', () => {
    const result = formatDate('2026-03-01T10:00:00Z')
    expect(result).toMatch(/01\/03\/2026/)
  })
})

describe('formatDateTime', () => {
  it('returns a string with date and time', () => {
    const result = formatDateTime('2026-03-01T14:30:00Z')
    expect(result).toContain('2026')
    expect(result).toContain('03')
    expect(result).toContain('01')
  })
})

describe('formatChartDateLabel', () => {
  it('returns a short day+month label in pt-BR', () => {
    const result = formatChartDateLabel('2026-03-01T10:00:00Z')
    expect(result).toMatch(/1\s+de\s+mar/i)
  })
})
