"use client";

import Link from "next/link";

/** Shown when the backend cannot answer (down, restarting, slow). */
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="container empty">
      <h1>Não conseguimos buscar os preços agora.</h1>
      <p className="muted" style={{ margin: "12px 0 24px" }}>
        Pode ser uma instabilidade passageira. Tente de novo em alguns segundos.
      </p>
      <button className="button" type="button" onClick={reset}>
        Tentar de novo
      </button>{" "}
      <Link href="/">Voltar ao início</Link>
    </main>
  );
}
