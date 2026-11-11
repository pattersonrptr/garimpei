/** Presentation rules for the public pages: money, time, stores, links. */

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function formatPrice(value: number | null | undefined): string {
  return value == null ? "—" : BRL.format(value);
}

/** "agora há pouco", "há 3 h", "há 2 dias": how fresh a price is. */
export function updatedAgo(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "ainda não verificado";
  const minutes = Math.floor((now.getTime() - new Date(iso).getTime()) / 60_000);
  if (minutes < 60) return "agora há pouco";
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `há ${hours} h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "há 1 dia" : `há ${days} dias`;
}

/** Store slugs (from the API) to the names visitors know. */
const STORE_NAMES: Record<string, string> = {
  estante_virtual: "Estante Virtual",
  livraria_da_vila: "Livraria da Vila",
  martins_fontes: "Martins Fontes",
  mercado_livre: "Mercado Livre",
  olx: "OLX",
  enjoei: "Enjoei",
};

export function storeName(slug: string): string {
  return (
    STORE_NAMES[slug] ??
    slug
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  );
}

/** "Cem anos de solidão" -> "cem-anos-de-solidao", for readable book URLs. */
export function slugify(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

/** The book page's address: ISBN first (what the page needs), title for people. */
export function bookPath(isbn13: string, title: string): string {
  const slug = slugify(title);
  return slug ? `/livro/${isbn13}-${slug}` : `/livro/${isbn13}`;
}

/** The ISBN at the start of a book page's address segment. */
export function isbnFromSegment(segment: string): string {
  return segment.split("-")[0];
}

/** How much cheaper used is than new, in whole percent (null if not cheaper). */
export function savingsPercent(
  used: number | null,
  newPrice: number | null,
): number | null {
  if (used == null || newPrice == null || newPrice <= 0 || used >= newPrice) {
    return null;
  }
  return Math.round((1 - used / newPrice) * 100);
}

/** "Livro" / "Livros" style counts in Portuguese. */
export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}
