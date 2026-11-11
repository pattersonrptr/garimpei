import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { cache } from "react";

import { Cover } from "@/components/BookCard";
import { OfferColumn } from "@/components/OfferColumn";
import { PriceChart } from "@/components/PriceChart";
import { SavingsBlock } from "@/components/SavingsBlock";
import { TopBar } from "@/components/TopBar";
import { getBook, getDailyLows } from "@/lib/api";
import { bookJsonLd } from "@/lib/seo";
import {
  amazonSearchUrl,
  bookPath,
  formatPrice,
  isbnFromSegment,
  offersIn,
} from "@/lib/format";

type Props = { params: Promise<{ slug: string }> };

/** One API call per request, shared by the metadata and the page. */
const loadBook = cache(async (segment: string) => getBook(isbnFromSegment(segment)));

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const book = await loadBook((await params).slug);
  if (!book) return { title: "Livro não encontrado" };
  const by = book.authors.length ? `, de ${book.authors.join(", ")}` : "";
  const from = [
    book.lowestUsed != null && `usado a partir de ${formatPrice(book.lowestUsed)}`,
    book.lowestNew != null && `novo a partir de ${formatPrice(book.lowestNew)}`,
  ]
    .filter(Boolean)
    .join(", ");
  return {
    title: `${book.title}: preço novo e usado`,
    description: `${book.title}${by}${from ? `: ${from}` : ""}. Compare livrarias e sebos.`,
    alternates: { canonical: bookPath(book.isbn13, book.title) },
  };
}

export default async function BookPage({ params }: Props) {
  const { slug } = await params;
  const book = await loadBook(slug);
  if (!book) notFound();

  // One address per book: fix a wrong or missing title part.
  const canonical = bookPath(book.isbn13, book.title);
  if (`/livro/${slug}` !== canonical) permanentRedirect(canonical);

  const lows = await getDailyLows(book.isbn13);
  const used = offersIn(book.offers, "used");
  const fresh = offersIn(book.offers, "new");
  const details = [book.publisher, book.year, book.pageCount && `${book.pageCount} páginas`]
    .filter(Boolean)
    .join(" · ");

  return (
    <>
      <TopBar />
      <script
        type="application/ld+json"
        // JSON.stringify output; "<" is escaped so the text cannot close the tag.
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(bookJsonLd(book, canonical)).replace(/</g, "\\u003c"),
        }}
      />
      <main className="container book">
        <header className="book-header">
          <Cover url={book.coverUrl} title={book.title} />
          <div>
            <h1>{book.title}</h1>
            {book.subtitle && <p className="subtitle">{book.subtitle}</p>}
            {book.authors.length > 0 && <p>{book.authors.join(", ")}</p>}
            <p className="muted small">
              {details}
              {details && " · "}ISBN {book.isbn13}
            </p>
          </div>
        </header>

        <SavingsBlock lowestUsed={book.lowestUsed} lowestNew={book.lowestNew} />

        <div className="offer-columns">
          <OfferColumn title="Usados" offers={used} empty="Nenhum usado à venda agora." />
          <OfferColumn title="Novos" offers={fresh} empty="Nenhum novo à venda agora." />
        </div>

        <PriceChart lows={lows} />

        <aside className="elsewhere">
          <p>Também vale conferir:</p>
          <a
            className="button secondary"
            href={amazonSearchUrl(book.isbn13, process.env.AMAZON_ASSOCIATE_TAG)}
            target="_blank"
            rel="nofollow sponsored noopener"
          >
            Ver na Amazon ↗
          </a>
        </aside>

        {book.synopsis && (
          <details className="synopsis">
            <summary>Sinopse</summary>
            <p>{book.synopsis}</p>
          </details>
        )}
      </main>
    </>
  );
}
