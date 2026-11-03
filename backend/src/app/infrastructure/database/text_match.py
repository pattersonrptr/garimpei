"""
Accent- and case-insensitive matching of search terms against product titles.

Users type "microsservicos" and listings say "Microsserviços"; both must match.
The same rule is applied in SQL (``title_contains``) and in Python
(``fold_text``), so alerts, opportunities and the dashboard agree.

On PostgreSQL this uses the ``unaccent`` extension (created by a migration).
On other dialects (SQLite in the test suite) ``unaccent`` compiles to a no-op,
so queries still run; accent folding is then only exercised in Postgres.
"""

import unicodedata

from sqlalchemy import String, literal
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.functions import GenericFunction


class unaccent(GenericFunction):  # noqa: N801 - mirrors the SQL function name
    type = String()
    name = "unaccent"
    inherit_cache = True


@compiles(unaccent)
def _unaccent_noop(element, compiler, **kw):
    return compiler.process(element.clauses, **kw)


@compiles(unaccent, "postgresql")
def _unaccent_postgresql(element, compiler, **kw):
    return f"unaccent({compiler.process(element.clauses, **kw)})"


def title_contains(column, term: "str | ColumnElement[str]") -> ColumnElement[bool]:
    """SQL condition: ``term`` appears in ``column``, ignoring case and accents."""
    term_expr = literal(term, String) if isinstance(term, str) else term
    pattern = literal("%", String) + unaccent(term_expr) + literal("%", String)
    return unaccent(column).ilike(pattern)


def fold_text(text: str) -> str:
    """Lowercase and strip accents: "Microsserviços" -> "microsservicos"."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def text_contains(haystack: str, needle: str) -> bool:
    """Python counterpart of ``title_contains``."""
    return fold_text(needle) in fold_text(haystack)
