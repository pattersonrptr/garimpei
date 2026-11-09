/**
 * Product service.
 * All product-related API calls — returns typed domain objects.
 */

import { apiClient } from '@/api/client'
import { ENDPOINTS } from '@/api/endpoints'
import { unwrapCollection, unwrapSingle, wrapPayload } from '@/api/jsonapi'
import { logger } from '@/lib/logger'
import type { PaginatedResult, ProductListParams } from '@/types/api'
import type {
  Product,
  ProductCreatePayload,
  ProductUpdatePayload,
} from '@/types/product'

/** Raw attributes from the API (snake_case) */
interface RawProductAttributes {
  url: string
  title: string
  source_product_code?: string
  description?: string
  image_urls?: string
  city?: string
  state?: string
  condition: string
  seller_name?: string
  is_available: boolean
  source_website_id: number
  source_metadata?: Record<string, unknown>
  current_price?: number
  created_at?: string
  updated_at?: string
}

function toProduct(raw: RawProductAttributes & { id: string }): Product {
  return {
    id: raw.id,
    url: raw.url,
    title: raw.title,
    sourceProductCode: raw.source_product_code,
    description: raw.description,
    imageUrls: raw.image_urls,
    city: raw.city,
    state: raw.state,
    condition: raw.condition as Product['condition'],
    sellerName: raw.seller_name,
    isAvailable: raw.is_available,
    sourceWebsiteId: raw.source_website_id,
    sourceMetadata: raw.source_metadata,
    currentPrice: raw.current_price,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  }
}

function toApiPayload(
  payload: ProductCreatePayload | ProductUpdatePayload,
): Record<string, unknown> {
  return {
    url: payload.url,
    title: payload.title,
    source_product_code: payload.sourceProductCode,
    description: payload.description,
    image_urls: payload.imageUrls,
    city: payload.city,
    state: payload.state,
    condition: payload.condition,
    seller_name: payload.sellerName,
    is_available: payload.isAvailable,
    source_website_id: payload.sourceWebsiteId,
    source_metadata: payload.sourceMetadata,
  }
}

export async function getProducts(
  params: ProductListParams,
): Promise<PaginatedResult<Product>> {
  logger.debug('Fetching products', { params })
  const response = await apiClient.get(ENDPOINTS.products.list, { params })
  const result = unwrapCollection<RawProductAttributes>(response.data)
  return {
    items: result.items.map(toProduct),
    total: result.total,
  }
}

export async function getProductById(id: string): Promise<Product> {
  logger.debug('Fetching product by id', { id })
  const response = await apiClient.get(ENDPOINTS.products.byId(id))
  const raw = unwrapSingle<RawProductAttributes>(response.data)
  return toProduct(raw)
}

export async function createProduct(
  payload: ProductCreatePayload,
): Promise<Product> {
  logger.info('Creating product', { title: payload.title })
  const body = wrapPayload('product', toApiPayload(payload))
  const response = await apiClient.post(ENDPOINTS.products.list, body)
  const raw = unwrapSingle<RawProductAttributes>(response.data)
  return toProduct(raw)
}

export async function updateProduct(
  id: string,
  payload: ProductUpdatePayload,
): Promise<Product> {
  logger.info('Updating product', { id })
  const body = wrapPayload('product', toApiPayload(payload), id)
  const response = await apiClient.put(ENDPOINTS.products.byId(id), body)
  const raw = unwrapSingle<RawProductAttributes>(response.data)
  return toProduct(raw)
}

export async function deleteProduct(id: string): Promise<void> {
  logger.warn('Deleting product', { id })
  await apiClient.delete(ENDPOINTS.products.byId(id))
}
