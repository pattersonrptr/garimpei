"""The words of an alert notification, shared by the e-mail and the log.

Pure functions, no framework: the e-mail adapter (infrastructure) and the
notification use cases both use them, so the subject in the inbox and the
one recorded in the notification log are always the same.
"""

# Store slugs (as stored) to the names people know. Same list as the site's
# web/src/lib/format.ts.
STORE_NAMES: dict[str, str] = {
    "estante_virtual": "Estante Virtual",
    "livraria_da_vila": "Livraria da Vila",
    "martins_fontes": "Martins Fontes",
    "mercado_livre": "Mercado Livre",
    "olx": "OLX",
    "enjoei": "Enjoei",
}


def brl(value: float) -> str:
    """R$ in the Brazilian format: 1234.5 -> "R$ 1.234,50"."""
    us = f"{value:,.2f}"  # 1,234.50
    return "R$ " + us.replace(",", "_").replace(".", ",").replace("_", ".")


def store_name(slug: str) -> str:
    """ "estante_virtual" -> "Estante Virtual"; unknown slugs are title-cased."""
    return STORE_NAMES.get(slug) or " ".join(
        word.capitalize() for word in slug.split("_")
    )


def alert_subject(product: str, price: float, store_slug: str) -> str:
    """ "Baixou: A Divina Comédia por R$ 17,46 na Estante Virtual"."""
    return f"Baixou: {product} por {brl(price)} na {store_name(store_slug)}"
