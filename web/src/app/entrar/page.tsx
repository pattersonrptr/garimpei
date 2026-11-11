import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { SignInForm } from "@/components/AuthForms";
import { TopBar } from "@/components/TopBar";
import { safeNextPath } from "@/lib/nextPath";
import { getSessionToken } from "@/lib/session";

export const metadata: Metadata = { title: "Entrar", robots: { index: false } };

type Props = { searchParams: Promise<{ next?: string }> };

export default async function SignInPage({ searchParams }: Props) {
  const next = safeNextPath((await searchParams).next);
  if (await getSessionToken()) redirect(next ?? "/alertas");

  return (
    <>
      <TopBar />
      <main className="container auth">
        <h1>Entrar</h1>
        <p className="muted">Para criar e acompanhar seus alertas de preço.</p>
        <SignInForm next={next} />
      </main>
    </>
  );
}
