/**
 * Book service: the public catalog (GET /books/{isbn}, no login needed).
 * Used by the "warn me" page to show which book the alert is for.
 */

import { apiClient } from '@/api/client'
import { ENDPOINTS } from '@/api/endpoints'
import { unwrapSingle } from '@/api/jsonapi'

export interface Book {
  isbn13: string
  title: string
  authors: string[]
  coverUrl: string | null
  lowestNew: number | null
  lowestUsed: number | null
}

interface RawBookAttributes {
  isbn13: string
  title: string
  authors?: string[]
  cover_url?: string | null
  lowest_new?: number | null
  lowest_used?: number | null
}

export async function getBook(isbn: string): Promise<Book> {
  const response = await apiClient.get(ENDPOINTS.books.byIsbn(isbn))
  const raw = unwrapSingle<RawBookAttributes>(response.data)
  return {
    isbn13: raw.isbn13,
    title: raw.title,
    authors: raw.authors ?? [],
    coverUrl: raw.cover_url ?? null,
    lowestNew: raw.lowest_new ?? null,
    lowestUsed: raw.lowest_used ?? null,
  }
}
