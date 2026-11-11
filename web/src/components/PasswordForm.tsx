"use client";

import { useActionState } from "react";

import { type PasswordFormState, changePasswordAction } from "@/app/actions/account";
import { MIN_PASSWORD_LENGTH } from "@/lib/authMessages";

/** Change one's own password: the current one, then the new one twice. */
export function PasswordForm() {
  const [state, action, pending] = useActionState<PasswordFormState, FormData>(
    changePasswordAction,
    {},
  );
  return (
    <form action={action} className="auth-form">
      <label>
        Senha atual
        <input name="current" type="password" autoComplete="current-password" required />
      </label>
      <label>
        Nova senha
        <input
          name="next"
          type="password"
          autoComplete="new-password"
          minLength={MIN_PASSWORD_LENGTH}
          required
        />
        <span className="muted small">Pelo menos {MIN_PASSWORD_LENGTH} caracteres.</span>
      </label>
      <label>
        Repita a nova senha
        <input
          name="confirm"
          type="password"
          autoComplete="new-password"
          minLength={MIN_PASSWORD_LENGTH}
          required
        />
      </label>
      {state.error && (
        <p className="form-error" role="alert">
          {state.error}
        </p>
      )}
      {state.done && (
        <p className="notice" role="status">
          Senha trocada. Use a nova senha da próxima vez que entrar.
        </p>
      )}
      <button className="button" type="submit" disabled={pending}>
        {pending ? "Trocando…" : "Trocar senha"}
      </button>
    </form>
  );
}
