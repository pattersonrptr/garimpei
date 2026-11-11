/**
 * Where to go after an administrator logs in.
 *
 * A back-office address opened while logged out is kept in `?next=` and
 * reopened after login. Only paths inside this app are accepted, so a
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
