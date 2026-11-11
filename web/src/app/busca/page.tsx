import type { Metadata } from "next";
import Link from "next/link";

import { BookCard } from "@/components/BookCard";
import { TopBar } from "@/components/TopBar";
import { PAGE_SIZE, searchBooks } from "@/lib/api";
import { plural } from "@/lib/format";

type Props = { searchParams: Promise<{ q?: string; pagina?: string }> };

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { q = "" } = await searchParams;
  return {
    title: q ? `Busca: ${q}` : "Busca",
    // Result pages change daily and repeat the book pages: keep them out of indexes.
    robots: { index: false, follow: true },
  };
}

export default async function SearchPage({ searchParams }: Props) {
  const { q = "", pagina } = await searchParams;
  const query = q.trim();
  const page = Math.max(1, Number.parseInt(pagina ?? "1", 10) || 1);
  const { books, total } =
    query.length >= 2 ? await searchBooks(query, page) : { books: [], total: 0 };
  const pages = Math.ceil(total / PAGE_SIZE);
  const pageHref = (n: number) =>
    `/busca?${new URLSearchParams({ q: query, pagina: String(n) })}`;

  return (
    <>
      <TopBar query={query} />
      <main className="container">
        <div className="results-header">
          <h1>{query ? `Resultados para “${query}”` : "Buscar livros"}</h1>
          {query && (
            <p className="muted">
              {plural(total, "livro encontrado", "livros encontrados")}
            </p>
          )}
        </div>

        {books.length > 0 ? (
          <ul className="results">
            {books.map((book) => (
              <li key={book.isbn13}>
                <BookCard book={book} />
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty">
            <p>
              {query.length < 2
                ? "Digite pelo menos duas letras do título, do autor ou o ISBN."
                : "Nenhum livro encontrado. Tente outro título, o sobrenome do autor ou o ISBN."}
            </p>
          </div>
        )}

        {pages > 1 && (
          <nav className="pager" aria-label="Páginas de resultados">
            {page > 1 ? <Link href={pageHref(page - 1)}>← Anteriores</Link> : <span />}
            <span className="muted">
              Página {page} de {pages}
            </span>
            {page < pages ? <Link href={pageHref(page + 1)}>Próximos →</Link> : <span />}
          </nav>
        )}
      </main>
    </>
  );
}
