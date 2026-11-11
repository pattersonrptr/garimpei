/**
 * The public Garimpei site (Next.js). Since Phase 5e this Vite app is the
 * admin back office only: everything a user does lives on the site.
 */

const SITE = (import.meta.env.VITE_SITE_URL ?? 'http://localhost:3000').replace(/\/+$/, '')

/** An address on the site; ``path`` starts with "/". */
export function siteUrl(path = '/', base: string = SITE): string {
  return `${base.replace(/\/+$/, '')}${path.startsWith('/') ? path : `/${path}`}`
}
