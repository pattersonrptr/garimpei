import "server-only";

import { type Result, toResult } from "@/lib/apiResult";
import { type Session, authedFetch } from "@/lib/session";

/** The signed-in user's account on the backend (GET /auth/me, PUT /auth/password). */

export interface Account {
  username: string;
  email: string;
  isStaff: boolean;
  createdAt: string | null;
}

export async function getAccount(session: Session, here: string): Promise<Account> {
  const response = await authedFetch(session, "/auth/me", here);
  if (!response.ok) throw new Error(`GET /auth/me: ${response.status}`);
  const a = (await response.json()).data.attributes;
  return {
    username: a.username,
    email: a.email,
    isStaff: Boolean(a.is_staff || a.is_superuser),
    createdAt: a.created_at ?? null,
  };
}

export async function changePassword(
  session: Session,
  here: string,
  currentPassword: string,
  newPassword: string,
): Promise<Result> {
  const response = await authedFetch(session, "/auth/password", here, {
    method: "PUT",
    body: JSON.stringify({
      data: {
        type: "password_change",
        attributes: { current_password: currentPassword, new_password: newPassword },
      },
    }),
  });
  return toResult(response);
}
