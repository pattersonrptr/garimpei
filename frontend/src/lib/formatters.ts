/**
 * Date and currency formatters used across the application.
 *
 * They follow the active UI language (dates "01/03/2026" in pt-BR,
 * "03/01/2026" in en). Prices stay in BRL in every language: the listings
 * come from Brazilian marketplaces.
 */

import { currentLanguage } from '@/i18n'

/** Format a date string to a short date: "01/03/2026" (pt-BR) */
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString(currentLanguage(), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** Format a date string to short label for charts: "1 mar" */
export function formatChartDateLabel(isoString: string): string {
  return new Date(isoString).toLocaleDateString(currentLanguage(), {
    month: 'short',
    day: 'numeric',
  })
}

/** Format a date string to full datetime: "11/04/2026, 14:30:00" */
export function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString(currentLanguage(), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

/** Format a number as BRL: "R$ 1.234,56" (pt-BR), "R$1,234.56" (en) */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat(currentLanguage(), {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

/** Short date + time without year/seconds: "11/04, 14:30" (pt-BR) */
export function formatShortDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString(currentLanguage(), {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
