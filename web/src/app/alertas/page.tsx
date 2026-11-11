import type { Metadata } from "next";

import { signOutAction } from "@/app/actions/session";
import { TopBar } from "@/components/TopBar";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Meus alertas", robots: { index: false } };

/** Placeholder for 5b: proves the session works. The list arrives in 5c. */
export default async function MyAlertsPage() {
  const { claims } = await requireSession("/alertas");
  return (
    <>
      <TopBar />
      <main className="container auth">
        <h1>Meus alertas</h1>
        <p>Olá, {claims.sub}.</p>
        <form action={signOutAction}>
          <button className="button secondary small" type="submit">
            Sair
          </button>
        </form>
      </main>
    </>
  );
}
