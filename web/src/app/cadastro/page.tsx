import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { SignUpForm } from "@/components/AuthForms";
import { TopBar } from "@/components/TopBar";
import { safeNextPath } from "@/lib/nextPath";
import { getSessionToken } from "@/lib/session";

export const metadata: Metadata = { title: "Criar conta", robots: { index: false } };

type Props = { searchParams: Promise<{ next?: string }> };

export default async function SignUpPage({ searchParams }: Props) {
  const next = safeNextPath((await searchParams).next);
  if (await getSessionToken()) redirect(next ?? "/alertas");

  return (
    <>
      <TopBar />
      <main className="container auth">
        <h1>Criar conta</h1>
        <p className="muted">
          Grátis. Usamos o e-mail só para avisar quando um preço baixar.
        </p>
        <SignUpForm next={next} />
      </main>
    </>
  );
}
