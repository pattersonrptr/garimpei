/**
 * Reading the "warn me" link from the public book page:
 * /alertas/novo?isbn=…&condicao=usado&preco=25.90
 */

import type { BookCondition } from '@/types/priceAlert'

/** The public site speaks Portuguese in its links: usado / novo / qualquer. */
const CONDITION_FROM_LINK: Record<string, BookCondition> = {
  usado: 'used',
  novo: 'new',
  qualquer: 'any',
  used: 'used',
  new: 'new',
  any: 'any',
}

export function conditionFromLink(raw: string | null): BookCondition {
  return CONDITION_FROM_LINK[raw ?? ''] ?? 'any'
}

/** The suggested price as the form shows it ("25.90"), or "" when missing or invalid. */
export function priceFromLink(raw: string | null): string {
  const value = Number(raw)
  return raw && Number.isFinite(value) && value > 0 ? value.toFixed(2) : ''
}

/** What the person typed ("25,90" or "25.90") as a number; NaN when invalid. */
export function parsePrice(text: string): number {
  const value = Number(text.trim().replace(',', '.'))
  return text.trim() && Number.isFinite(value) && value > 0 ? value : NaN
}
