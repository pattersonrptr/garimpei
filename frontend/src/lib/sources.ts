/**
 * Readable names for the marketplaces. The API identifies them by a slug
 * ("estante_virtual"); people know them as brands ("Estante Virtual").
 * Brand names are the same in every language, so they are not translated.
 */

const BRANDS: Record<string, string> = {
  enjoei: 'Enjoei',
  estante_virtual: 'Estante Virtual',
  livraria_da_vila: 'Livraria da Vila',
  martins_fontes: 'Martins Fontes',
  mercado_livre: 'Mercado Livre',
  olx: 'OLX',
}

export function sourceDisplayName(slug: string): string {
  const known = BRANDS[slug.toLowerCase()]
  if (known) return known
  return slug
    .split(/[_-]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
