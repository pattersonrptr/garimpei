import type { Metadata } from "next";
import Link from "next/link";

import { signOutAction } from "@/app/actions/session";
import { PasswordForm } from "@/components/PasswordForm";
import { TopBar } from "@/components/TopBar";
import { getAccount } from "@/lib/accountApi";
import { parseUtc } from "@/lib/myAlerts";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Minha conta", robots: { index: false } };

const SINCE = new Intl.DateTimeFormat("pt-BR", {
  month: "long",
  year: "numeric",
  timeZone: "America/Sao_Paulo",
});

/** Phase 5d: who is signed in, change password, sign out. Plans come later. */
export default async function AccountPage() {
  const session = await requireSession("/conta");
  const account = await getAccount(session, "/conta");

  return (
    <>
      <TopBar />
      <main className="container auth">
        <h1>Minha conta</h1>

        <dl className="account-facts">
          <dt>Usuário</dt>
          <dd>{account.username}</dd>
          <dt>E-mail</dt>
          <dd>{account.email}</dd>
          {account.createdAt && (
            <>
              <dt>Desde</dt>
              <dd>{SINCE.format(parseUtc(account.createdAt))}</dd>
            </>
          )}
        </dl>
        <p className="small">
          <Link href="/alertas">Ver meus alertas</Link>
        </p>

        <section className="account-section">
          <h2>Trocar senha</h2>
          <PasswordForm />
        </section>

        <section className="account-section">
          <form action={signOutAction}>
            <button className="button secondary" type="submit">
              Sair
            </button>
          </form>
        </section>
      </main>
    </>
  );
}
