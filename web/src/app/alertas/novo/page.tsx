import type { Metadata } from "next";
import Link from "next/link";

import { NewAlertForm } from "@/components/AlertForms";
import { TopBar } from "@/components/TopBar";
import { getBook } from "@/lib/api";
import { bookPath, formatPrice } from "@/lib/format";
import { conditionFromLink, priceFromLink } from "@/lib/myAlerts";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Criar alerta", robots: { index: false } };

type Props = { searchParams: Promise<{ isbn?: string; condicao?: string; preco?: string }> };

/** "Warn me" (Phase 5c): /alertas/novo?isbn=…&condicao=usado&preco=25 */
export default async function NewAlertPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
  );
  await requireSession(`/alertas/novo?${query}`);

  const isbn = params.isbn ?? "";
  const book = isbn ? await getBook(isbn) : null;
  const condition = conditionFromLink(params.condicao);

  return (
    <>
      <TopBar />
      <main className="container auth">
        <h1>Criar alerta</h1>
        {!book ? (
          <>
            <p className="form-error">Não encontramos esse produto.</p>
            <p>
              <Link href="/">Buscar um produto</Link>
            </p>
          </>
        ) : (
          <>
            <div className="alert-product">
              {book.coverUrl && <img src={book.coverUrl} alt="" width={56} />}
              <div>
                <p className="alert-title">
                  <Link href={bookPath(book.isbn13, book.title)}>{book.title}</Link>
                </p>
                {book.authors.length > 0 && <p className="muted small">{book.authors.join(", ")}</p>}
                <p className="small">
                  Hoje: usado {formatPrice(book.lowestUsed)} · novo {formatPrice(book.lowestNew)}
                </p>
              </div>
            </div>
            <NewAlertForm isbn={book.isbn13} condition={condition} price={priceFromLink(params.preco)} />
          </>
        )}
      </main>
    </>
  );
}
