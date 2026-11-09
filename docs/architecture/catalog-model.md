# Catalog model

Decision record, Nov 2026 (price comparator plan, Phase 1b).

## Model

```text
CanonicalProduct ──1:N── ProductIdentifier      (isbn13 today; ean, asin... later)
       │  category, title, attributes (JSON: author, publisher, year, ...)
       └──1:N── Product  (the offer; has price history, source website, condition)
                 └─ canonical_product_id  (nullable)
```

- `canonical_products`: the product itself, independent of any store.
  Category-specific data lives in the `attributes` JSON, so a new category
  needs no new columns.
- `product_identifiers`: one row per code, unique on `(kind, value)`. Looking a
  product up by ISBN is a lookup on this table.
- `products.canonical_product_id`: nullable foreign key. Existing offers, price
  history and alerts are untouched; old rows stay unlinked until matched.

**Decision: `Product` stays as the offer.** It already has what an offer
needs (url, source, condition, availability, price history). Renaming it to
`Offer` touches the controllers, schemas and the scrapers' API contract, so it
waits until there is a reason (Phase 2 or 3).

## Looking up a book

`GetOrCreateBookByIsbnUseCase(products, metadata)`:

1. `IsbnMatcher` normalizes the ISBN (10 or 13, hyphens ignored) to ISBN-13, or
   rejects it (`InvalidIsbnError`).
2. If a product has that identifier, return it. No outside call.
3. Otherwise ask the metadata source. Unknown book: `BookNotFoundError`;
   source down: `BookMetadataUnavailableError`. Nothing is stored in either case.
4. Create the canonical product with its identifier. If another request created
   it first (unique constraint), return that one.

## Boundaries

The use case defines what it needs; adapters plug in behind it.

| Port (in `catalog/ports.py`) | Adapter |
|---|---|
| `BookMetadataGateway` | `catalog/adapters/brasilapi_books.py` (BrasilAPI `/isbn/v1`) |
| `CanonicalProductRepositoryInterface` | `catalog/persistence/repositories.py` |

Matching is a strategy per category (`catalog/matching.py`): another category
adds a matcher next to `IsbnMatcher`.

`backend/src/scripts/add_book.py` is the composition root for now:

```bash
cd backend && python -m src.scripts.add_book 978-85-359-1484-9
```

## Not done on purpose

- No HTTP endpoint yet. The first consumer (offer collection, Phase 2, or the
  public pages, Phase 3) decides its shape.
- Offers are not matched to canonical products yet (Phase 2).
- `PriceAlert` does not target a canonical product yet (Phase 4).
- Only BrasilAPI. The port allows adding a second source as a fallback.
