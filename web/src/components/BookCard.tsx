import Link from "next/link";

import { bookPath, formatPrice } from "@/lib/format";
import type { BookSummary } from "@/lib/types";

export function Cover({ url, title }: { url: string | null; title: string }) {
  if (!url) {
    return (
      <div className="cover cover-placeholder" aria-hidden="true">
        {title.charAt(0).toUpperCase()}
      </div>
    );
  }
  // Covers come from the book metadata (BrasilAPI), never from a store.
  return <img className="cover" src={url} alt="" loading="lazy" />;
}

export function BookCard({ book }: { book: BookSummary }) {
  const hasPrice = book.lowestUsed != null || book.lowestNew != null;
  return (
    <Link href={bookPath(book.isbn13, book.title)} className="book-card">
      <Cover url={book.coverUrl} title={book.title} />
      <div>
        <h2>{book.title}</h2>
        {book.authors.length > 0 && (
          <p className="muted">{book.authors.join(", ")}</p>
        )}
        {hasPrice ? (
          <div className="prices">
            {book.lowestUsed != null && (
              <div>
                <span className="price-label">Usado a partir de</span>
                <span className="price used">{formatPrice(book.lowestUsed)}</span>
              </div>
            )}
            {book.lowestNew != null && (
              <div>
                <span className="price-label">Novo a partir de</span>
                <span className="price">{formatPrice(book.lowestNew)}</span>
              </div>
            )}
          </div>
        ) : (
          <p className="muted">Sem oferta em estoque agora</p>
        )}
      </div>
    </Link>
  );
}
