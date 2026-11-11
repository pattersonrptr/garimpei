import { type NextRequest, NextResponse } from "next/server";

import { secondsLeft } from "@/lib/jwt";

/**
 * Keeps the session alive on the account pages (Phase 5, decision 2).
 *
 * The backend's token lasts 30 minutes. When less than ten are left, the
 * token is renewed (POST /auth/refresh-token, which needs the still-valid
 * token) and the new one replaces the cookie. No session, or an expired one:
 * sign in again and come back.
 */

const SESSION_COOKIE = "garimpei_session"; // same as lib/session (proxy runs apart)
const RENEW_BELOW_SECONDS = 10 * 60;
const API_URL = process.env.API_URL ?? "http://localhost:8000";

function signIn(request: NextRequest): NextResponse {
  const url = new URL("/entrar", request.url);
  url.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  const response = NextResponse.redirect(url);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}

export async function proxy(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const left = secondsLeft(token);
  if (!token || left === null || left <= 0) return signIn(request);
  if (left > RENEW_BELOW_SECONDS) return NextResponse.next();

  try {
    const renewed = await fetch(`${API_URL}/auth/refresh-token`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!renewed.ok) return signIn(request);
    const attributes = (await renewed.json()).data.attributes;
    const response = NextResponse.next();
    response.cookies.set(SESSION_COOKIE, attributes.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: request.nextUrl.protocol === "https:",
      path: "/",
      maxAge: attributes.expires_in * 60,
    });
    return response;
  } catch {
    // Backend unreachable: keep the current token; the page will say so.
    return NextResponse.next();
  }
}

export const config = {
  matcher: ["/alertas/:path*", "/conta/:path*"],
};
