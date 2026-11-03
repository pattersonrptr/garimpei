"""Tests for accent/case-insensitive term matching (text_match)."""

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.dialects import postgresql, sqlite

from src.app.infrastructure.database.text_match import (
    fold_text,
    text_contains,
    title_contains,
)

products = Table(
    "products",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("title", String),
)


@pytest.mark.parametrize(
    "raw,folded",
    [
        ("Microsserviços", "microsservicos"),
        ("ARQUITETURA LIMPA", "arquitetura limpa"),
        ("Programação Clara", "programacao clara"),
        ("Lúcia á é í ó ú ã õ â ê ô à ü", "lucia a e i o u a o a e o a u"),
        ("plain", "plain"),
    ],
)
def test_fold_text(raw, folded):
    assert fold_text(raw) == folded


@pytest.mark.parametrize(
    "title,term,expected",
    [
        ("Migrando Sistemas Monolíticos para Microsserviços", "microsservicos", True),
        ("Migrando Sistemas Monolíticos para Microsserviços", "MICROSSERVIÇOS", True),
        ("Python Fluente | Luciano Ramalho", "python fluente", True),
        ("escova bigode - limpa desenhos", "arquitetura limpa", False),
    ],
)
def test_text_contains(title, term, expected):
    assert text_contains(title, term) is expected


def _compile(expr, dialect):
    return str(expr.compile(dialect=dialect))


def test_title_contains_uses_unaccent_on_postgresql():
    sql = _compile(
        title_contains(products.c.title, "microsservicos"), postgresql.dialect()
    )
    assert "unaccent(products.title)" in sql
    assert "ILIKE" in sql.upper()
    assert sql.count("unaccent(") == 2


def test_title_contains_is_plain_ilike_elsewhere():
    sql = _compile(title_contains(products.c.title, "microsservicos"), sqlite.dialect())
    assert "unaccent" not in sql
    assert "lower(products.title) LIKE" in sql


def test_title_contains_accepts_a_column_term():
    alerts = Table("alerts", MetaData(), Column("search_term", String))
    sql = _compile(
        title_contains(products.c.title, alerts.c.search_term), postgresql.dialect()
    )
    assert "unaccent(alerts.search_term)" in sql
