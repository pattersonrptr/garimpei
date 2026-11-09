/**
 * Which of my alerts found a listing, and how much I save.
 *
 * Mirrors the backend rule (backend/src/app/infrastructure/database/text_match.py):
 * an alert matches a listing when its search term appears in the title,
 * ignoring case and accents, and the listing comes from one of the alert's
 * sources. It is an opportunity when the price is at or below the max price.
 */

import type { PriceAlert } from '@/types/priceAlert'
import type { Product } from '@/types/product'

/** Lowercase and strip accents: "Microsserviços" -> "microsservicos". */
export function foldText(text: string): string {
  return text.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('en')
}

export function alertMatchesProduct(alert: PriceAlert, product: Pick<Product, 'title' | 'sourceWebsiteId'>): boolean {
  const term = foldText(alert.searchTerm).trim()
  if (!term || !foldText(product.title).includes(term)) return false
  return alert.sourceWebsiteIds.map(Number).includes(Number(product.sourceWebsiteId))
}

export interface AlertMatch {
  alert: PriceAlert
  /** Max price minus current price; negative when the listing costs more. */
  savings: number | null
  isOpportunity: boolean
}

/** My alerts that match a listing, opportunities first, biggest savings first. */
export function matchesForProduct(
  alerts: PriceAlert[],
  product: Pick<Product, 'title' | 'sourceWebsiteId' | 'currentPrice'>,
): AlertMatch[] {
  const price = product.currentPrice
  return alerts
    .filter((alert) => alertMatchesProduct(alert, product))
    .map((alert) => {
      const savings = price == null ? null : alert.maxPrice - price
      return { alert, savings, isOpportunity: savings != null && savings >= 0 }
    })
    .sort((a, b) => (b.savings ?? -Infinity) - (a.savings ?? -Infinity))
}
