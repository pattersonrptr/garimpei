/** PriceAlert domain types — mirrors backend PriceAlertAttributes */

/** What a book alert watches (Phase 4). */
export type BookCondition = 'new' | 'used' | 'any'

export interface PriceAlert {
  id: string
  searchTerm: string
  maxPrice: number
  isActive: boolean
  frequencyMinutes: number
  lastTriggeredAt?: string | null
  userId?: number | null
  searchConfigId?: number | null
  sourceWebsiteIds: number[]
  /** Set on book alerts: the book (search term holds its title). */
  canonicalProductId?: number | null
  condition?: BookCondition | null
  createdAt?: string
  updatedAt?: string
}

export interface PriceAlertCreatePayload {
  /** A keyword alert sends searchTerm; a book alert sends isbn and condition. */
  searchTerm?: string
  isbn?: string
  condition?: BookCondition
  maxPrice: number
  userId: number
  isActive?: boolean
  frequencyMinutes?: number
  sourceWebsiteIds?: number[]
}

export interface PriceAlertUpdatePayload {
  searchTerm?: string
  maxPrice?: number
  isActive?: boolean
  frequencyMinutes?: number
  sourceWebsiteIds?: number[]
}
