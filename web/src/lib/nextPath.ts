/**
 * Where to go after signing in or up (`?next=`).
 *
 * Protected pages send visitors to /entrar?next=<the page>. Only paths inside
 * this site are accepted, so a crafted link cannot send someone to another
 * site after they sign in (open redirect).
 */

/** A safe in-site path from a `next` parameter, or null. */
export function safeNextPath(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (!raw.startsWith("/")) return null; // absolute URLs, "javascript:", …
  if (raw.startsWith("//") || raw.startsWith("/\\")) return null; // other hosts
  if ([...raw].some((char) => char.charCodeAt(0) < 0x20)) return null; // newlines…
  return raw;
}

/** "/entrar?next=%2Falertas" (or just "/entrar"). */
export function withNext(path: string, next: string | null | undefined): string {
  const safe = safeNextPath(next);
  return safe ? `${path}?next=${encodeURIComponent(safe)}` : path;
}
