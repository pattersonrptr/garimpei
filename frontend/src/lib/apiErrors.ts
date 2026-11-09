/**
 * Turn API errors into messages in the user's language.
 *
 * The API explains plan limits with a machine-readable `meta`
 * ({ limit, value, plan }) next to an English `detail`; the UI uses the
 * meta so the message follows the selected language.
 */

import type { TFunction } from 'i18next'

export interface ApiErrorObject {
  status?: string
  code?: string
  detail?: string
  meta?: Record<string, unknown>
}

/** The first JSON:API error of an axios-style error, if any. */
export function firstApiError(err: unknown): { status?: number; error?: ApiErrorObject } {
  const response = (err as { response?: { status?: number; data?: { errors?: ApiErrorObject[] } } })
    ?.response
  return { status: response?.status, error: response?.data?.errors?.[0] }
}

export type PlanLimitName =
  | 'max_active_alerts'
  | 'min_frequency_minutes'
  | 'max_sources'
  | 'manual_run_interval'

/**
 * A localized explanation for a PLAN_LIMIT_REACHED error, or null when the
 * error is something else.
 */
export function planLimitMessage(err: unknown, t: TFunction<'common'>): string | null {
  const { error } = firstApiError(err)
  if (error?.code !== 'PLAN_LIMIT_REACHED') return null
  const limit = error.meta?.limit as PlanLimitName | undefined
  const value = Number(error.meta?.value)
  const wait = Number(error.meta?.wait_minutes)
  switch (limit) {
    case 'max_active_alerts':
      return t('planLimit.maxActiveAlerts', { count: value })
    case 'min_frequency_minutes':
      return t('planLimit.minFrequency', { count: value })
    case 'max_sources':
      return t('planLimit.maxSources', { count: value })
    case 'manual_run_interval':
      return t('planLimit.manualRun', { count: value, wait })
    default:
      return error.detail ?? null
  }
}
