"""ISBN rules and the ISBN matcher (pure, no database or network)."""

import pytest

from src.app.catalog.entities import IdentifierKind
from src.app.catalog.isbn import InvalidIsbnError, normalize_isbn
from src.app.catalog.matching import IsbnMatcher

ISBN13 = "9788535914849"  # 1984, Companhia das Letras
ISBN10 = "8535914846"


class TestNormalizeIsbn:
    def test_isbn13_is_returned_as_is(self):
        assert normalize_isbn(ISBN13) == ISBN13

    def test_isbn10_is_converted_to_isbn13(self):
        assert normalize_isbn(ISBN10) == ISBN13

    @pytest.mark.parametrize(
        "raw", ["978-85-359-1484-9", " 978 85 359 1484 9 ", "85-359-1484-6"]
    )
    def test_hyphens_and_spaces_are_ignored(self, raw):
        assert normalize_isbn(raw) == ISBN13

    def test_isbn10_ending_in_x_is_accepted(self):
        # 0-8044-2957-X is the classic ISBN-10 with an X check digit.
        assert normalize_isbn("080442957X") == "9780804429573"

    def test_lowercase_x_is_accepted(self):
        assert normalize_isbn("080442957x") == "9780804429573"

    @pytest.mark.parametrize(
        "raw",
        [
            "9788535914848",  # wrong check digit
            "8535914847",  # wrong ISBN-10 check digit
            "978853591484",  # too short
            "97885359148490",  # too long
            "97885359148AB",  # letters
            "9771234567003",  # valid check digit but not a book prefix
            "",
            "   ",
            None,
        ],
    )
    def test_invalid_values_are_rejected(self, raw):
        with pytest.raises(InvalidIsbnError):
            normalize_isbn(raw)


class TestIsbnMatcher:
    def test_identifies_a_valid_isbn_as_isbn13(self):
        identifier = IsbnMatcher().identify("85-359-1484-6")

        assert identifier.kind == IdentifierKind.ISBN13
        assert identifier.value == ISBN13

    def test_returns_none_when_the_text_is_not_an_isbn(self):
        assert IsbnMatcher().identify("iPhone 13 128GB") is None
