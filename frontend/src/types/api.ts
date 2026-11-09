/**
 * Generic JSON:API types matching the backend's common/jsonapi module.
 * Every response from the API follows this shape.
 */

/** A single resource object as returned by the API */
export interface ResourceObject<TAttributes> {
  id: string
  type: string
  attributes: TAttributes
  relationships?: Record<string, unknown>
}

/** Response wrapping a single resource */
export interface SingleResourceResponse<TAttributes> {
  data: ResourceObject<TAttributes>
  meta?: Record<string, unknown>
}

/** Response wrapping a collection of resources */
export interface CollectionResponse<TAttributes> {
  data: ResourceObject<TAttributes>[]
  meta?: {
    total?: number
    [key: string]: unknown
  }
  links?: Record<string, string>
}

/** JSON:API error object */
export interface JsonApiError {
  status: string
  code: string
  title: string
  detail: string
  source?: {
    pointer?: string
    parameter?: string
  }
}

/** JSON:API error response */
export interface JsonApiErrorResponse {
  errors: JsonApiError[]
}

/** Pagination parameters shared across all list requests */
export interface PaginationParams {
  limit: number
  offset: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

/** Filters the products list understands (GET /products/) */
export interface ProductListParams extends PaginationParams {
  title?: string
  condition?: string
  is_available?: boolean
  opportunities_only?: boolean
}

/** Paginated result returned by services after unwrapping the API response */
export interface PaginatedResult<T> {
  items: T[]
  total: number
}
