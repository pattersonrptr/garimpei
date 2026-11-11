/**
 * PriceAlert service.
 * All price-alert-related API calls — returns typed domain objects.
 */

import { apiClient } from '@/api/client'
import { ENDPOINTS } from '@/api/endpoints'
import { unwrapCollection, unwrapSingle, wrapPayload } from '@/api/jsonapi'
import { logger } from '@/lib/logger'
import type { PaginationParams, PaginatedResult } from '@/types/api'
import type {
  PriceAlert,
  PriceAlertCreatePayload,
  PriceAlertUpdatePayload,
} from '@/types/priceAlert'

/** Raw attributes from the API (snake_case) */
interface RawPriceAlertAttributes {
  search_term: string
  max_price: number
  is_active: boolean
  frequency_minutes: number
  last_triggered_at?: string | null
  user_id?: number | null
  search_config_id?: number | null
  source_website_ids: number[]
  canonical_product_id?: number | null
  condition?: PriceAlert['condition']
  created_at?: string
  updated_at?: string
}

function toPriceAlert(
  raw: RawPriceAlertAttributes & { id: string },
): PriceAlert {
  return {
    id: raw.id,
    searchTerm: raw.search_term,
    maxPrice: raw.max_price,
    isActive: raw.is_active,
    frequencyMinutes: raw.frequency_minutes,
    lastTriggeredAt: raw.last_triggered_at,
    userId: raw.user_id,
    searchConfigId: raw.search_config_id,
    sourceWebsiteIds: raw.source_website_ids ?? [],
    canonicalProductId: raw.canonical_product_id ?? null,
    condition: raw.condition ?? null,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  }
}

function toApiPayload(
  p: PriceAlertCreatePayload | PriceAlertUpdatePayload,
): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  if ('searchTerm' in p && p.searchTerm !== undefined)
    result.search_term = p.searchTerm
  if ('maxPrice' in p && p.maxPrice !== undefined) result.max_price = p.maxPrice
  if ('isActive' in p && p.isActive !== undefined) result.is_active = p.isActive
  if ('frequencyMinutes' in p && p.frequencyMinutes !== undefined)
    result.frequency_minutes = p.frequencyMinutes
  if ('sourceWebsiteIds' in p && p.sourceWebsiteIds !== undefined)
    result.source_website_ids = p.sourceWebsiteIds
  if ('isbn' in p && p.isbn !== undefined) result.isbn = p.isbn
  if ('condition' in p && p.condition !== undefined) result.condition = p.condition
  if ('userId' in p && (p as PriceAlertCreatePayload).userId !== undefined)
    result.user_id = (p as PriceAlertCreatePayload).userId
  return result
}

export async function getPriceAlerts(
  params: PaginationParams,
): Promise<PaginatedResult<PriceAlert>> {
  logger.debug('Fetching price alerts', { params })
  const response = await apiClient.get(ENDPOINTS.priceAlerts.list, { params })
  const result = unwrapCollection<RawPriceAlertAttributes>(response.data)
  return { items: result.items.map(toPriceAlert), total: result.total }
}

export async function getPriceAlertsByUser(
  userId: number,
): Promise<PriceAlert[]> {
  logger.debug('Fetching price alerts for user', { userId })
  const response = await apiClient.get(ENDPOINTS.priceAlerts.byUser(userId))
  const result = unwrapCollection<RawPriceAlertAttributes>(response.data)
  return result.items.map(toPriceAlert)
}

export async function getPriceAlertById(id: string): Promise<PriceAlert> {
  logger.debug('Fetching price alert', { id })
  const response = await apiClient.get(ENDPOINTS.priceAlerts.byId(id))
  const raw = unwrapSingle<RawPriceAlertAttributes>(response.data)
  return toPriceAlert(raw)
}

export async function createPriceAlert(
  payload: PriceAlertCreatePayload,
): Promise<PriceAlert> {
  logger.debug('Creating price alert', { payload })
  const body = wrapPayload('price_alert', toApiPayload(payload))
  const response = await apiClient.post(ENDPOINTS.priceAlerts.list, body)
  const raw = unwrapSingle<RawPriceAlertAttributes>(response.data)
  return toPriceAlert(raw)
}

export async function updatePriceAlert(
  id: string,
  payload: PriceAlertUpdatePayload,
): Promise<PriceAlert> {
  logger.debug('Updating price alert', { id, payload })
  const body = wrapPayload('price_alert', toApiPayload(payload), id)
  const response = await apiClient.put(ENDPOINTS.priceAlerts.byId(id), body)
  const raw = unwrapSingle<RawPriceAlertAttributes>(response.data)
  return toPriceAlert(raw)
}

export async function deletePriceAlert(id: string): Promise<void> {
  logger.debug('Deleting price alert', { id })
  await apiClient.delete(ENDPOINTS.priceAlerts.byId(id))
}
