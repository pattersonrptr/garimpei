"""
Load source website fixtures into the database.

This script populates the database with the basic source websites
(OLX, Enjoei, Mercado Livre, Estante Virtual, Livraria da Vila, Martins Fontes)
needed for product tracking.

The bookstores are inactive: they only receive offers from the ISBN collectors
(scrapers/src/collectors). An inactive store is not offered for keyword
alerts, which need a keyword scraper they do not have.

Names are the slugs the scrapers, collectors and frontend use
(``estante_virtual``); the frontend shows the brand (``src/lib/sources.ts``).
"""

from sqlalchemy.orm import Session

from src.app.infrastructure.database.models.source_website_model import SourceWebsite
from src.app.infrastructure.database_config import SessionLocal


def load_source_websites():
    """Load source website fixtures into the database."""
    fixtures = [
        {
            "id": 1,
            "name": "olx",
            "base_url": "https://www.olx.com.br/brasil",
            "is_active": True,
        },
        {
            "id": 2,
            "name": "enjoei",
            "base_url": "https://enjusearch.enjoei.com.br",
            "is_active": True,
        },
        {
            "id": 3,
            "name": "mercado_livre",
            "base_url": "https://lista.mercadolivre.com.br",
            "is_active": True,
        },
        {
            "id": 4,
            "name": "estante_virtual",
            "base_url": "https://www.estantevirtual.com.br",
            "is_active": True,
        },
        {
            "id": 5,
            "name": "livraria_da_vila",
            "base_url": "https://www.livrariadavila.com.br",
            "is_active": False,
        },
        {
            "id": 6,
            "name": "martins_fontes",
            "base_url": "https://www.martinsfontespaulista.com.br",
            "is_active": False,
        },
    ]

    db: Session = SessionLocal()
    try:
        for fixture_data in fixtures:
            # Check if source website already exists
            existing = (
                db.query(SourceWebsite)
                .filter(SourceWebsite.id == fixture_data["id"])
                .first()
            )

            if existing:
                print(
                    f"✓ Source website '{fixture_data['name']}' already exists (ID: {fixture_data['id']})"
                )
                continue

            # Create new source website
            source_website = SourceWebsite(**fixture_data)
            db.add(source_website)
            db.commit()
            db.refresh(source_website)
            print(
                f"✓ Created source website: {source_website.name} (ID: {source_website.id})"
            )

        print("\n✓ Source website fixtures loaded successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error loading fixtures: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Loading source website fixtures...\n")
    load_source_websites()
