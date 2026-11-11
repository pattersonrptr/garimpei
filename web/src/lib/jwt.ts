/**
 * Reading the backend's JWT without verifying it: the backend verifies it on
 * every call. The site only needs to know who is signed in and when the
 * token runs out (to renew it in time).
 */

export interface TokenClaims {
  sub?: string; // username
  user_id?: number;
  email?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  exp?: number; // seconds since 1970
}

export function tokenClaims(token: string | null | undefined): TokenClaims | null {
  const payload = token?.split(".")[1];
  if (!payload) return null;
  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = Buffer.from(base64, "base64").toString("utf8");
    const claims = JSON.parse(json);
    return claims && typeof claims === "object" ? (claims as TokenClaims) : null;
  } catch {
    return null;
  }
}

/** Seconds until the token expires (negative once it has); null if unreadable. */
export function secondsLeft(token: string | null | undefined, now = Date.now()): number | null {
  const exp = tokenClaims(token)?.exp;
  return typeof exp === "number" ? Math.floor(exp - now / 1000) : null;
}
