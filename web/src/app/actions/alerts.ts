"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createBookAlert, deleteAlert, updateAlert } from "@/lib/alertsApi";
import type { ApiError } from "@/lib/authMessages";
import { conditionFromLink, newAlertPath, parsePrice } from "@/lib/myAlerts";
import { requireSession } from "@/lib/session";

const MY_ALERTS = "/alertas";

export interface AlertFormState {
  error?: string;
  /** Set when the alert already exists: the page links to "Meus alertas". */
  duplicate?: boolean;
  values?: Record<string, string>;
}

const TRY_AGAIN = "Não foi possível salvar agora. Tente de novo em instantes.";

function saveMessage(error: ApiError): string {
  if (error.code === "PLAN_LIMIT_REACHED") {
    return "Você chegou ao limite de alertas ativos. Pause ou exclua um alerta para criar outro.";
  }
  if (error.status === 404) return "Não encontramos esse produto.";
  if (error.status === 422 || error.status === 400) return "Confira o preço.";
  return TRY_AGAIN;
}

export async function createAlertAction(_: AlertFormState, form: FormData): Promise<AlertFormState> {
  const isbn = String(form.get("isbn") ?? "");
  const condition = conditionFromLink(String(form.get("condition") ?? ""));
  const priceText = String(form.get("price") ?? "");
  const values = { condition, price: priceText };
  const maxPrice = parsePrice(priceText);
  if (Number.isNaN(maxPrice)) return { error: "Digite um preço maior que zero, como 25,90.", values };

  const here = newAlertPath(isbn, condition, maxPrice);
  const session = await requireSession(here);
  const saved = await createBookAlert(session, here, { isbn, condition, maxPrice });
  if (!saved.ok) {
    if (saved.error.status === 409) return { duplicate: true, values };
    return { error: saveMessage(saved.error), values };
  }
  revalidatePath(MY_ALERTS);
  redirect(`${MY_ALERTS}?criado=1`);
}

export async function changePriceAction(_: AlertFormState, form: FormData): Promise<AlertFormState> {
  const id = String(form.get("id") ?? "");
  const priceText = String(form.get("price") ?? "");
  const maxPrice = parsePrice(priceText);
  if (Number.isNaN(maxPrice)) {
    return { error: "Digite um preço maior que zero.", values: { price: priceText } };
  }
  const session = await requireSession(MY_ALERTS);
  const saved = await updateAlert(session, MY_ALERTS, id, { maxPrice });
  if (!saved.ok) return { error: saveMessage(saved.error), values: { price: priceText } };
  revalidatePath(MY_ALERTS);
  return {};
}

/** Pause and resume: plain forms, so they also work without JavaScript. */
export async function setActiveAction(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  const active = form.get("active") === "true";
  const session = await requireSession(MY_ALERTS);
  const saved = await updateAlert(session, MY_ALERTS, id, { isActive: active });
  revalidatePath(MY_ALERTS);
  if (!saved.ok) {
    redirect(`${MY_ALERTS}?erro=${saved.error.code === "PLAN_LIMIT_REACHED" ? "limite" : "salvar"}`);
  }
  redirect(MY_ALERTS);
}

export async function deleteAlertAction(form: FormData): Promise<void> {
  const id = String(form.get("id") ?? "");
  const session = await requireSession(MY_ALERTS);
  const deleted = await deleteAlert(session, MY_ALERTS, id);
  revalidatePath(MY_ALERTS);
  redirect(deleted.ok ? `${MY_ALERTS}?excluido=1` : `${MY_ALERTS}?erro=salvar`);
}
