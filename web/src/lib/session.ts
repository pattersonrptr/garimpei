import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { API_URL } from "@/lib/api";
import { type TokenClaims, tokenClaims } from "@/lib/jwt";
import { withNext } from "@/lib/nextPath";
import { siteUrl } from "@/lib/seo";

/**
 * The signed-in user's session: the backend's JWT in an httpOnly cookie
 * (Phase 5, decision 2). Page JavaScript never sees the token; the Next.js
 * server sends it to the backend as a Bearer token.
 */

export const SESSION_COOKIE = "garimpei_session";

export function sessionCookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: siteUrl().startsWith("https://"),
    path: "/",
    maxAge: Math.max(0, Math.floor(maxAgeSeconds)),
  };
}

export async function getSessionToken(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

/** Server Actions only: Next.js lets only actions and route handlers write cookies. */
export async function saveSession(token: string, expiresInMinutes: number): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, token, sessionCookieOptions(expiresInMinutes * 60));
}

export async function clearSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

export interface Session {
  token: string;
  claims: TokenClaims;
}

/** The session, or a redirect to /entrar that comes back to ``here``. */
export async function requireSession(here: string): Promise<Session> {
  const token = await getSessionToken();
  const claims = tokenClaims(token);
  if (!token || !claims) redirect(withNext("/entrar", here));
  return { token, claims };
}

/**
 * A call to the backend as the signed-in user. A refused token (401, or 403
 * with no token) sends the user to sign in again and come back to ``here``.
 */
export async function authedFetch(
  session: Session,
  path: string,
  here: string,
  init: RequestInit = {},
): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/vnd.api+json",
      ...(init.body ? { "Content-Type": "application/vnd.api+json" } : {}),
      ...init.headers,
      Authorization: `Bearer ${session.token}`,
    },
  });
  if (response.status === 401 || response.status === 403) {
    redirect(withNext("/entrar", here));
  }
  return response;
}
