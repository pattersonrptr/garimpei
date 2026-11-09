"""LoadSeedBooksUseCase and the seed CSV reader (no database, no network)."""

import pytest

from src.app.catalog.entities import BookMetadata
from src.app.catalog.ports import BookMetadataGateway, BookMetadataUnavailableError
from src.app.catalog.use_cases import GetOrCreateBookByIsbnUseCase, LoadSeedBooksUseCase
from src.scripts.load_seed_books import DEFAULT_FILE, read_seed_isbns
from src.tests.unit.catalog.test_get_or_create_book import InMemoryProducts

ORWELL = "9788535914849"
OTHER = "9780306406157"


class MetadataByIsbn(BookMetadataGateway):
    """Knows some ISBNs, fails on others, and counts calls."""

    def __init__(self, known=(), failing=()):
        self.known, self.failing, self.calls = set(known), set(failing), []

    def fetch(self, isbn13):
        self.calls.append(isbn13)
        if isbn13 in self.failing:
            raise BookMetadataUnavailableError("timeout")
        if isbn13 in self.known:
            return BookMetadata(isbn13=isbn13, title=f"Book {isbn13}")
        return None


def loader(metadata, products=None):
    products = products or InMemoryProducts()
    pauses = []
    use_case = LoadSeedBooksUseCase(
        GetOrCreateBookByIsbnUseCase(products, metadata),
        products,
        pause=lambda: pauses.append(1),
    )
    return use_case, products, pauses


def test_creates_every_known_book():
    use_case, products, pauses = loader(MetadataByIsbn(known={ORWELL, OTHER}))

    report = use_case.execute([ORWELL, "978-0-306-40615-7"])

    assert report.created == [ORWELL, OTHER]
    assert report.failed == []
    assert len(products.stored) == 2
    assert len(pauses) == 2  # one pause per outside lookup


def test_running_twice_creates_nothing_new_and_skips_lookups():
    metadata = MetadataByIsbn(known={ORWELL})
    use_case, products, pauses = loader(metadata)
    use_case.execute([ORWELL])

    second = use_case.execute([ORWELL])

    assert second.created == []
    assert second.existing == [ORWELL]
    assert metadata.calls == [ORWELL]
    assert len(products.stored) == 1
    assert len(pauses) == 1


def test_bad_entries_are_reported_and_do_not_stop_the_rest():
    metadata = MetadataByIsbn(known={ORWELL}, failing={OTHER})
    use_case, products, _ = loader(metadata)

    report = use_case.execute(["123", OTHER, "9788535902778", ORWELL])

    assert report.created == [ORWELL]
    assert [isbn for isbn, _ in report.failed] == ["123", OTHER, "9788535902778"]
    reasons = dict(report.failed)
    assert reasons["123"] == "invalid ISBN"
    assert "unavailable" in reasons[OTHER]
    assert reasons["9788535902778"] == "unknown to the metadata source"


class TestReadSeedIsbns:
    def test_reads_the_isbn13_column_skipping_blanks(self, tmp_path):
        path = tmp_path / "seed.csv"
        path.write_text(
            "isbn13,title_br\n9788535914849,1984\n,sem isbn\n 9780306406157 ,x\n",
            encoding="utf-8",
        )

        assert read_seed_isbns(path) == [ORWELL, OTHER]

    def test_a_file_without_the_column_is_rejected(self, tmp_path):
        path = tmp_path / "seed.csv"
        path.write_text("isbn,title\n9788535914849,1984\n", encoding="utf-8")

        with pytest.raises(ValueError, match="isbn13"):
            read_seed_isbns(path)


def test_the_shipped_seed_list_has_50_valid_unique_isbns():
    from src.app.catalog.isbn import normalize_isbn

    isbns = read_seed_isbns(DEFAULT_FILE)

    assert len(isbns) == 50
    assert len({normalize_isbn(i) for i in isbns}) == 50
