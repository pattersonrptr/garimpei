import "server-only";

import type { ApiError } from "@/lib/authMessages";
import { type AlertCondition, type MyAlert, toMyAlert } from "@/lib/myAlerts";
import { type Session, authedFetch } from "@/lib/session";

/**
 * The signed-in user's alerts on the backend (GET /me/alerts and
 * /price-alerts). ``here`` is where a refused session comes back after signing in.
 */

export type Result = { ok: true } | { ok: false; error: ApiError };

async function result(response: Response): Promise<Result> {
  if (response.ok) return { ok: true };
  try {
    const error = (await response.json())?.errors?.[0];
    return { ok: false, error: { status: response.status, code: error?.code, pointer: error?.source?.pointer } };
  } catch {
    return { ok: false, error: { status: response.status } };
  }
}

export async function listMyAlerts(session: Session, here: string): Promise<MyAlert[]> {
  const response = await authedFetch(session, "/me/alerts", here);
  if (!response.ok) throw new Error(`GET /me/alerts: ${response.status}`);
  const body = await response.json();
  return ((body?.data as Record<string, unknown>[]) ?? []).map(toMyAlert);
}

export async function createBookAlert(
  session: Session,
  here: string,
  alert: { isbn: string; condition: AlertCondition; maxPrice: number },
): Promise<Result> {
  const response = await authedFetch(session, "/price-alerts/", here, {
    method: "POST",
    body: JSON.stringify({
      data: {
        type: "price_alert",
        attributes: {
          isbn: alert.isbn,
          condition: alert.condition,
          max_price: alert.maxPrice,
          user_id: session.claims.user_id,
        },
      },
    }),
  });
  return result(response);
}

export async function updateAlert(
  session: Session,
  here: string,
  id: string,
  changes: { maxPrice?: number; isActive?: boolean },
): Promise<Result> {
  const attributes: Record<string, unknown> = {};
  if (changes.maxPrice !== undefined) attributes.max_price = changes.maxPrice;
  if (changes.isActive !== undefined) attributes.is_active = changes.isActive;
  const response = await authedFetch(session, `/price-alerts/${encodeURIComponent(id)}`, here, {
    method: "PUT",
    body: JSON.stringify({ data: { type: "price_alert", id, attributes } }),
  });
  return result(response);
}

export async function deleteAlert(session: Session, here: string, id: string): Promise<Result> {
  const response = await authedFetch(session, `/price-alerts/${encodeURIComponent(id)}`, here, {
    method: "DELETE",
  });
  return result(response);
}
