"""Tests for normalizers module."""

from __future__ import annotations

import pytest

from src.excel_engine.normalizers import (
    DEFAULT_UNIT_MAP,
    normalize_arabic,
    normalize_header,
    normalize_number,
    normalize_persian,
    normalize_unit,
    normalize_whitespace,
)


class TestNormalizePersian:
    def test_arabic_kaf_replaced(self) -> None:
        # Arabic Kaf ك → Persian Kaf ک
        result = normalize_persian("\u0643\u062a\u0627\u0628")
        assert "\u0643" not in result

    def test_arabic_ya_replaced(self) -> None:
        # Arabic Ya ي → Persian Ya ی
        result = normalize_persian("\u06cc\u0627")
        assert "\u064a" not in result

    def test_alef_variants_normalized(self) -> None:
        # آ, أ, إ, ٱ all become ا
        variants = ["\u0622", "\u0623", "\u0625", "\u0671"]
        for v in variants:
            assert normalize_persian(v) == "\u0627"

    def test_diacritics_removed(self) -> None:
        # Arabic diacritic (kasra, fatha, etc.) should be stripped
        with_diacritic = "\u0643\u0650\u062a\u0627\u0628"  # كِتاب
        result = normalize_persian(with_diacritic)
        assert "\u0650" not in result

    def test_persian_numerals_converted(self) -> None:
        result = normalize_persian("\u06f1\u06f2\u06f3")
        assert result == "123"

    def test_eastern_arabic_numerals_converted(self) -> None:
        result = normalize_persian("\u0661\u0662\u0663")
        assert result == "123"

    def test_strips_whitespace(self) -> None:
        assert normalize_persian("  hello  ") == "hello"

    def test_plain_ascii_unchanged(self) -> None:
        assert normalize_persian("hello world") == "hello world"


class TestNormalizeArabic:
    def test_alef_variants_normalized(self) -> None:
        for v in ["\u0622", "\u0623", "\u0625", "\u0671"]:
            assert normalize_arabic(v) == "\u0627"

    def test_diacritics_removed(self) -> None:
        result = normalize_arabic("\u0643\u0650\u062a\u0627\u0628")
        assert "\u0650" not in result

    def test_eastern_arabic_numerals_to_ascii(self) -> None:
        result = normalize_arabic("\u0660\u0661\u0662")
        assert result == "012"

    def test_strips_whitespace(self) -> None:
        assert normalize_arabic("  \u0643\u062a\u0627\u0628  ") == "\u0643\u062a\u0627\u0628"


class TestNormalizeHeader:
    def test_lowercase(self) -> None:
        assert normalize_header("ProductName") == "productname"

    def test_spaces_to_underscores(self) -> None:
        assert normalize_header("Unit Price") == "unit_price"

    def test_hyphens_to_underscores(self) -> None:
        assert normalize_header("unit-price") == "unit_price"

    def test_multiple_spaces_collapsed(self) -> None:
        assert normalize_header("a  b") == "a_b"

    def test_leading_trailing_stripped(self) -> None:
        assert normalize_header("  name  ") == "name"

    def test_dots_removed(self) -> None:
        result = normalize_header("item.no")
        assert "." not in result

    def test_consecutive_underscores_collapsed(self) -> None:
        result = normalize_header("a__b")
        assert "__" not in result


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self) -> None:
        assert normalize_whitespace("a   b   c") == "a b c"

    def test_strips_ends(self) -> None:
        assert normalize_whitespace("  hello  ") == "hello"

    def test_tabs_collapsed(self) -> None:
        assert normalize_whitespace("a\t\tb") == "a b"


class TestNormalizeNumber:
    def test_integer_string(self) -> None:
        assert normalize_number("42") == 42.0

    def test_float_string(self) -> None:
        assert normalize_number("3.14") == pytest.approx(3.14)

    def test_thousands_comma(self) -> None:
        assert normalize_number("1,000,000") == 1_000_000.0

    def test_arabic_comma_thousands(self) -> None:
        assert normalize_number("1\u060c000") == 1000.0

    def test_european_format(self) -> None:
        # "1.234,56" → 1234.56
        result = normalize_number("1.234,56")
        assert result == pytest.approx(1234.56)

    def test_persian_digits(self) -> None:
        result = normalize_number("\u06f1\u06f2\u06f3")
        assert result == 123.0

    def test_invalid_returns_none(self) -> None:
        assert normalize_number("not_a_number") is None

    def test_empty_returns_none(self) -> None:
        assert normalize_number("   ") is None


class TestNormalizeUnit:
    def test_kg_to_kilogram(self) -> None:
        assert normalize_unit("kg") == "kilogram"

    def test_case_insensitive(self) -> None:
        assert normalize_unit("KG") == "kilogram"
        assert normalize_unit("Kg") == "kilogram"

    def test_kgs_to_kilogram(self) -> None:
        assert normalize_unit("kgs") == "kilogram"

    def test_pcs_to_piece(self) -> None:
        assert normalize_unit("pcs") == "piece"

    def test_dollar_sign_to_usd(self) -> None:
        assert normalize_unit("$") == "USD"

    def test_persian_rial(self) -> None:
        assert normalize_unit("\u0631\u06cc\u0627\u0644") == "IRR"

    def test_unknown_unit_returned_lowercased(self) -> None:
        result = normalize_unit("lightyear")
        assert result == "lightyear"

    def test_custom_unit_map(self) -> None:
        custom = {"widget": "WDG"}
        assert normalize_unit("widget", unit_map=custom) == "WDG"

    def test_strips_whitespace(self) -> None:
        assert normalize_unit("  kg  ") == "kilogram"

    def test_default_map_not_empty(self) -> None:
        assert len(DEFAULT_UNIT_MAP) > 5
