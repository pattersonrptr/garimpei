import { formatPrice, storeName, updatedAgo } from "@/lib/format";
import type { Offer } from "@/lib/types";

/** One condition's offers (used or new), in stock and cheapest first. */
export function OfferColumn({
  title,
  offers,
  empty,
  alertHref,
}: {
  title: string;
  offers: Offer[];
  empty: string;
  /** "Warn me" link to the logged-in app (Phase 4d); hidden when null. */
  alertHref?: string | null;
}) {
  return (
    <section className="offer-column">
      <h2>{title}</h2>
      {offers.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <ul>
          {offers.map((offer) => (
            <li key={offer.url} className={offer.isAvailable ? "offer" : "offer sold-out"}>
              <div>
                <p className="store">{storeName(offer.store)}</p>
                <p className="muted small">Atualizado {updatedAgo(offer.lastCheckedAt)}</p>
              </div>
              <div className="offer-action">
                <p className="price">
                  {offer.isAvailable ? formatPrice(offer.price) : "Esgotado"}
                </p>
                {offer.isAvailable && (
                  <a
                    className="button small"
                    href={offer.url}
                    target="_blank"
                    rel="nofollow sponsored noopener"
                  >
                    Ver na loja
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {alertHref && (
        <a className="button secondary small warn-me" href={alertHref} rel="nofollow">
          🔔 Me avise quando baixar
        </a>
      )}
    </section>
  );
}
