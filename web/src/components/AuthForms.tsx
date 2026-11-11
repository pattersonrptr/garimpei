"use client";

import Link from "next/link";
import { useActionState } from "react";

import { type FormState, signInAction, signUpAction } from "@/app/actions/session";
import { MIN_PASSWORD_LENGTH } from "@/lib/authMessages";
import { withNext } from "@/lib/nextPath";

/**
 * Sign-in and sign-up forms. They post to Server Actions, so they also work
 * before the page's JavaScript loads; with it, errors show without a reload.
 */

function ErrorMessage({ state }: { state: FormState }) {
  if (!state.error) return null;
  return (
    <p className="form-error" role="alert">
      {state.error}
    </p>
  );
}

export function SignInForm({ next }: { next: string | null }) {
  const [state, action, pending] = useActionState(signInAction, {});
  return (
    <form action={action} className="auth-form">
      <input type="hidden" name="next" value={next ?? ""} />
      <label>
        E-mail ou usuário
        <input
          name="login"
          autoComplete="username"
          defaultValue={state.values?.login}
          required
          autoFocus
        />
      </label>
      <label>
        Senha
        <input name="password" type="password" autoComplete="current-password" required />
      </label>
      <ErrorMessage state={state} />
      <button className="button" type="submit" disabled={pending}>
        {pending ? "Entrando…" : "Entrar"}
      </button>
      <p className="muted small">
        Ainda não tem conta? <Link href={withNext("/cadastro", next)}>Criar conta</Link>
      </p>
    </form>
  );
}

export function SignUpForm({ next }: { next: string | null }) {
  const [state, action, pending] = useActionState(signUpAction, {});
  return (
    <form action={action} className="auth-form">
      <input type="hidden" name="next" value={next ?? ""} />
      <label>
        Nome de usuário
        <input
          name="username"
          autoComplete="username"
          defaultValue={state.values?.username}
          required
          autoFocus
        />
      </label>
      <label>
        E-mail
        <input
          name="email"
          type="email"
          autoComplete="email"
          defaultValue={state.values?.email}
          required
        />
      </label>
      <label>
        Senha
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={MIN_PASSWORD_LENGTH}
          required
        />
        <span className="muted small">Pelo menos {MIN_PASSWORD_LENGTH} caracteres.</span>
      </label>
      <ErrorMessage state={state} />
      <button className="button" type="submit" disabled={pending}>
        {pending ? "Criando…" : "Criar conta"}
      </button>
      <p className="muted small">
        Já tem conta? <Link href={withNext("/entrar", next)}>Entrar</Link>
      </p>
    </form>
  );
}
