"use server";

import { redirect } from "next/navigation";

import { API_URL } from "@/lib/api";
import {
  type ApiError,
  signInMessage,
  signUpMessage,
  signUpProblem,
} from "@/lib/authMessages";
import { safeNextPath } from "@/lib/nextPath";
import { clearSession, saveSession } from "@/lib/session";

/** Where a signed-in user lands when the link did not say. */
const HOME_AFTER_SIGN_IN = "/alertas";

export interface FormState {
  error?: string;
  /** What the user typed, so a failed attempt does not empty the form. */
  values?: Record<string, string>;
}

function field(form: FormData, name: string): string {
  return String(form.get(name) ?? "").trim();
}

async function firstError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();
    const error = body?.errors?.[0];
    return {
      status: response.status,
      code: error?.code,
      pointer: error?.source?.pointer,
    };
  } catch {
    return { status: response.status };
  }
}

type SignIn = { ok: true; token: string; expiresIn: number } | { ok: false; error: ApiError };

async function signIn(login: string, password: string): Promise<SignIn> {
  try {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: login, password }),
      cache: "no-store",
    });
    if (!response.ok) return { ok: false, error: await firstError(response) };
    const attributes = (await response.json()).data.attributes;
    return { ok: true, token: attributes.access_token, expiresIn: attributes.expires_in };
  } catch {
    return { ok: false, error: { status: 503 } };
  }
}

export async function signInAction(_: FormState, form: FormData): Promise<FormState> {
  const login = field(form, "login");
  const password = String(form.get("password") ?? "");
  const values = { login };
  if (!login || !password) return { error: "Preencha o e-mail (ou usuário) e a senha.", values };

  const result = await signIn(login, password);
  if (!result.ok) return { error: signInMessage(result.error), values };

  await saveSession(result.token, result.expiresIn);
  redirect(safeNextPath(field(form, "next")) ?? HOME_AFTER_SIGN_IN);
}

export async function signUpAction(_: FormState, form: FormData): Promise<FormState> {
  const fields = {
    username: field(form, "username"),
    email: field(form, "email"),
    password: String(form.get("password") ?? ""),
  };
  const values = { username: fields.username, email: fields.email };
  const problem = signUpProblem(fields);
  if (problem) return { error: problem, values };

  try {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/vnd.api+json" },
      body: JSON.stringify({ data: { type: "users", attributes: fields } }),
      cache: "no-store",
    });
    if (!response.ok) return { error: signUpMessage(await firstError(response)), values };
  } catch {
    return { error: signUpMessage({ status: 503 }), values };
  }

  // The account exists: sign in right away instead of asking again.
  const result = await signIn(fields.username, fields.password);
  if (!result.ok) redirect("/entrar");
  await saveSession(result.token, result.expiresIn);
  redirect(safeNextPath(field(form, "next")) ?? HOME_AFTER_SIGN_IN);
}

export async function signOutAction(): Promise<void> {
  await clearSession();
  redirect("/");
}
