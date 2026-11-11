"use server";

import { changePassword } from "@/lib/accountApi";
import { passwordChangeMessage, passwordChangeProblem } from "@/lib/authMessages";
import { requireSession } from "@/lib/session";

const ACCOUNT = "/conta";

export interface PasswordFormState {
  error?: string;
  done?: boolean;
}

export async function changePasswordAction(
  _: PasswordFormState,
  form: FormData,
): Promise<PasswordFormState> {
  const fields = {
    current: String(form.get("current") ?? ""),
    next: String(form.get("next") ?? ""),
    confirm: String(form.get("confirm") ?? ""),
  };
  const problem = passwordChangeProblem(fields);
  if (problem) return { error: problem };

  const session = await requireSession(ACCOUNT);
  const changed = await changePassword(session, ACCOUNT, fields.current, fields.next);
  if (!changed.ok) return { error: passwordChangeMessage(changed.error) };
  return { done: true };
}
