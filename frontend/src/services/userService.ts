/**
 * User service.
 * Handles user registration (public) and user management (staff/superuser).
 */

import { apiClient } from '@/api/client'
import { ENDPOINTS } from '@/api/endpoints'
import { unwrapCollection, unwrapSingle, wrapPayload } from '@/api/jsonapi'
import { logger } from '@/lib/logger'
import type { PaginatedResult, PaginationParams } from '@/types/api'
import type { User } from '@/types/user'

/** Raw attributes from the API (snake_case) */
interface RawUserAttributes {
  username: string
  email: string
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  created_at?: string
  updated_at?: string
}

function toUser(raw: RawUserAttributes & { id: string }): User {
  return {
    id: raw.id,
    username: raw.username,
    email: raw.email,
    isActive: raw.is_active,
    isStaff: raw.is_staff,
    isSuperuser: raw.is_superuser,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  }
}

export interface UserCreatePayload {
  username: string
  email: string
  password: string
}

export interface UserUpdatePayload {
  username?: string
  email?: string
  isActive?: boolean
  isStaff?: boolean
  isSuperuser?: boolean
}

/** List users (staff or superuser only). */
export async function getUsers(
  params: PaginationParams,
): Promise<PaginatedResult<User>> {
  logger.debug('Fetching users', { params })
  const response = await apiClient.get(ENDPOINTS.users.list, { params })
  const result = unwrapCollection<RawUserAttributes>(response.data)
  return {
    items: result.items.map(toUser),
    total: result.total,
  }
}

/** Get a single user by ID (staff or superuser only). */
export async function getUserById(id: string): Promise<User> {
  logger.debug('Fetching user', { id })
  const response = await apiClient.get(ENDPOINTS.users.byId(id))
  const raw = unwrapSingle<RawUserAttributes>(response.data)
  return toUser(raw)
}

/** Update a user (superuser only). */
export async function updateUser(
  id: string,
  payload: UserUpdatePayload,
): Promise<User> {
  logger.info('Updating user', { id })
  const body = wrapPayload(
    'users',
    {
      username: payload.username,
      email: payload.email,
      is_active: payload.isActive,
      is_staff: payload.isStaff,
      is_superuser: payload.isSuperuser,
    },
    id,
  )
  const response = await apiClient.put(ENDPOINTS.users.byId(id), body)
  const raw = unwrapSingle<RawUserAttributes>(response.data)
  return toUser(raw)
}

/** Delete a user (superuser only). */
export async function deleteUser(id: string): Promise<void> {
  logger.warn('Deleting user', { id })
  await apiClient.delete(ENDPOINTS.users.byId(id))
}
