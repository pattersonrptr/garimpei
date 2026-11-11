/**
 * Where to go after login or sign-up.
 *
 * The public book pages (Next.js) send visitors to /alertas/novo?isbn=…;
 * when they are not logged in, the app keeps that address in `?next=` and
 * returns there afterwards. Only paths inside this app are accepted, so a
 * crafted link cannot send someone to another site after they log in.
 */

/** A safe in-app path from a `next` parameter, or null. */
export function safeNextPath(raw: string | null | undefined): string | null {
  if (!raw) return null
  if (!raw.startsWith('/')) return null // absolute URLs, "javascript:", …
  if (raw.startsWith('//') || raw.startsWith('/\\')) return null // other hosts
  if ([...raw].some((char) => char.charCodeAt(0) < 0x20)) return null // newlines…
  return raw
}

/** "/login?next=%2Falertas%2Fnovo%3Fisbn%3D…" (or just "/login"). */
export function withNext(path: string, next: string | null | undefined): string {
  const safe = safeNextPath(next)
  return safe ? `${path}?next=${encodeURIComponent(safe)}` : path
}
