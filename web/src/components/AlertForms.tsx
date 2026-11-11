"use client";

import Link from "next/link";
import { useActionState } from "react";

import { type AlertFormState, changePriceAction, createAlertAction } from "@/app/actions/alerts";
import type { AlertCondition } from "@/lib/myAlerts";

function ErrorMessage({ error }: { error?: string }) {
  if (!error) return null;
  return (
    <p className="form-error" role="alert">
      {error}
    </p>
  );
}

const CONDITIONS: { value: AlertCondition; label: string }[] = [
  { value: "used", label: "Usado" },
  { value: "new", label: "Novo" },
  { value: "any", label: "Novo ou usado" },
];

/** "Warn me": the condition and the target price, suggested by the product page. */
export function NewAlertForm({
  isbn,
  condition,
  price,
}: {
  isbn: string;
  condition: AlertCondition;
  price: string;
}) {
  const [state, action, pending] = useActionState<AlertFormState, FormData>(createAlertAction, {});
  if (state.duplicate) {
    return (
      <div className="notice" role="status">
        <p>Você já tem um alerta para este produto nessa condição.</p>
        <Link className="button small" href="/alertas">
          Ver meus alertas
        </Link>
      </div>
    );
  }
  return (
    <form action={action} className="auth-form">
      <input type="hidden" name="isbn" value={isbn} />
      <fieldset className="choices">
        <legend>Quais exemplares?</legend>
        {CONDITIONS.map((option) => (
          <label key={option.value} className="choice">
            <input
              type="radio"
              name="condition"
              value={option.value}
              defaultChecked={(state.values?.condition ?? condition) === option.value}
            />
            {option.label}
          </label>
        ))}
      </fieldset>
      <label>
        Me avise quando custar até
        <span className="money-input">
          <span aria-hidden="true">R$</span>
          <input
            name="price"
            inputMode="decimal"
            defaultValue={state.values?.price ?? price}
            placeholder="25,90"
            required
          />
        </span>
        <span className="muted small">Mandamos um e-mail quando alguma loja chegar nesse preço.</span>
      </label>
      <ErrorMessage error={state.error} />
      <button className="button" type="submit" disabled={pending}>
        {pending ? "Criando…" : "Criar alerta"}
      </button>
    </form>
  );
}

/** Change an alert's target price, inside its card. */
export function PriceForm({ id, price }: { id: string; price: string }) {
  const [state, action, pending] = useActionState<AlertFormState, FormData>(changePriceAction, {});
  return (
    <form action={action} className="price-form">
      <input type="hidden" name="id" value={id} />
      <label>
        Novo alvo
        <span className="money-input">
          <span aria-hidden="true">R$</span>
          <input
            name="price"
            inputMode="decimal"
            defaultValue={state.values?.price ?? price}
            required
          />
        </span>
      </label>
      <button className="button small" type="submit" disabled={pending}>
        {pending ? "Salvando…" : "Salvar"}
      </button>
      <ErrorMessage error={state.error} />
    </form>
  );
}
