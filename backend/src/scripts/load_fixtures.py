import argparse

from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.app.catalog.persistence.models import PriceHistory, Product
from src.app.fixtures.fixtures import get_fixtures
from src.app.infrastructure.database.models.plan_model import Plan
from src.app.infrastructure.database.models.search_config_model import SearchConfig
from src.app.infrastructure.database.models.search_config_source_website_model import (
    search_config_source_website,
)
from src.app.infrastructure.database.models.source_website_model import SourceWebsite
from src.app.infrastructure.database.models.user_model import User
from src.app.infrastructure.database_config import SessionLocal

FIXTURE_DEPENDENCIES = {
    "all": [
        "plans",
        "source_websites",
        "users",
        "products",
        "price_history",
        "search_configs",
    ],
    "plans": [],
    "users": [],
    "source_websites": [],
    "products": ["source_websites"],
    "price_history": ["products"],
    "search_configs": ["users", "source_websites"],
}

FIXTURE_INSERT_ORDER = [
    "plans",
    "source_websites",
    "users",
    "products",
    "price_history",
    "search_configs",
]


def resolve_dependencies(selected):
    resolved = set()

    def add_with_deps(fixture):
        if fixture not in resolved:
            for dep in FIXTURE_DEPENDENCIES.get(fixture, []):
                add_with_deps(dep)
            resolved.add(fixture)

    for f in selected:
        add_with_deps(f)
    # Returns the fixtures in the order they should be inserted
    return [f for f in FIXTURE_INSERT_ORDER if f in resolved]


def _upsert(db, model, rows):
    """Insert rows, skipping any that already exist (ON CONFLICT DO NOTHING)."""
    if not rows:
        return
    stmt = pg_insert(model.__table__).values(rows).on_conflict_do_nothing()
    db.execute(stmt)


def load_fixtures(selected_fixtures):
    db = SessionLocal()
    data = get_fixtures()
    try:
        if "plans" in selected_fixtures:
            _upsert(db, Plan, data.get("plans", []))

        if "source_websites" in selected_fixtures:
            _upsert(db, SourceWebsite, data["source_websites"])

        if "users" in selected_fixtures:
            _upsert(db, User, data.get("users", []))

        if "products" in selected_fixtures:
            _upsert(db, Product, data["products"])

        if "price_history" in selected_fixtures:
            _upsert(db, PriceHistory, data["price_history"])

        if "search_configs" in selected_fixtures:
            search_configs_data = []
            for sc in data["search_configs"]:
                sc_copy = sc.copy()
                sc_copy.pop("source_website_ids", None)
                search_configs_data.append(sc_copy)
            _upsert(db, SearchConfig, search_configs_data)

            search_config_source_website_data = []
            for sc in data["search_configs"]:
                search_config_id = sc["id"]
                source_website_ids = sc.get("source_website_ids", [])
                for sw_id in source_website_ids:
                    search_config_source_website_data.append(
                        {
                            "search_config_id": search_config_id,
                            "source_website_id": sw_id,
                        }
                    )
            if search_config_source_website_data:
                stmt = (
                    pg_insert(search_config_source_website)
                    .values(search_config_source_website_data)
                    .on_conflict_do_nothing()
                )
                db.execute(stmt)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load fixtures into the database.")
    parser.add_argument(
        "fixtures",
        nargs="+",
        choices=list(FIXTURE_DEPENDENCIES.keys()),
        help="Fixtures to be loaded (ex: users, source_websites, price_history, products, search_configs)",
    )
    args = parser.parse_args()
    fixtures_to_load = resolve_dependencies(args.fixtures)
    print(f"Loading fixtures: {fixtures_to_load}")
    load_fixtures(fixtures_to_load)
    print("Fixtures loaded successfully.")
