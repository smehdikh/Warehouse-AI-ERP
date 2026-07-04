"""Tests for column_mapper.ColumnMapper."""

from __future__ import annotations

from src.excel_engine.column_mapper import ColumnMapper

SAMPLE_MAPPING = {
    "product_id": ["id", "product id", "sku", "item_no", "item no"],
    "unit_price": ["price", "unit price", "cost", "rate"],
    "quantity": ["qty", "quantity", "count", "amount"],
}


class TestColumnMapper:
    def setup_method(self) -> None:
        self.mapper = ColumnMapper(mapping=SAMPLE_MAPPING)

    # ------------------------------------------------------------------
    # Exact match
    # ------------------------------------------------------------------

    def test_exact_alias_match(self) -> None:
        results = self.mapper.map_columns(["id"])
        assert results[0].mapped_field == "product_id"
        assert results[0].strategy == "exact"
        assert results[0].confidence == 1.0

    def test_exact_match_multiword(self) -> None:
        results = self.mapper.map_columns(["unit price"])
        assert results[0].mapped_field == "unit_price"

    # ------------------------------------------------------------------
    # Normalised match
    # ------------------------------------------------------------------

    def test_case_insensitive_normalised_match(self) -> None:
        results = self.mapper.map_columns(["SKU"])
        assert results[0].mapped_field == "product_id"
        assert results[0].strategy in {"exact", "normalized"}

    def test_normalised_match_with_spaces(self) -> None:
        results = self.mapper.map_columns(["Unit Price"])
        assert results[0].mapped_field == "unit_price"

    # ------------------------------------------------------------------
    # Keyword match
    # ------------------------------------------------------------------

    def test_keyword_match_partial(self) -> None:
        results = self.mapper.map_columns(["total qty"])
        assert results[0].mapped_field == "quantity"
        assert results[0].strategy == "keyword"

    # ------------------------------------------------------------------
    # No match
    # ------------------------------------------------------------------

    def test_no_match_returns_none(self) -> None:
        results = self.mapper.map_columns(["warehouse_location"])
        assert results[0].mapped_field is None
        assert results[0].strategy == "none"
        assert results[0].confidence == 0.0

    # ------------------------------------------------------------------
    # Multiple columns
    # ------------------------------------------------------------------

    def test_maps_multiple_columns(self) -> None:
        results = self.mapper.map_columns(["id", "price", "qty", "unknown"])
        assert results[0].mapped_field == "product_id"
        assert results[1].mapped_field == "unit_price"
        assert results[2].mapped_field == "quantity"
        assert results[3].mapped_field is None

    def test_output_length_matches_input(self) -> None:
        names = ["a", "b", "c", "d", "e"]
        results = self.mapper.map_columns(names)
        assert len(results) == len(names)

    # ------------------------------------------------------------------
    # Normalised name
    # ------------------------------------------------------------------

    def test_normalised_name_is_snake_case(self) -> None:
        results = self.mapper.map_columns(["Unit Price"])
        assert results[0].normalized_name == "unit_price"

    def test_normalised_name_strips_special_chars(self) -> None:
        results = self.mapper.map_columns(["Item No."])
        assert "." not in results[0].normalized_name

    # ------------------------------------------------------------------
    # Dynamic mapping update
    # ------------------------------------------------------------------

    def test_set_mapping_replaces_index(self) -> None:
        mapper = ColumnMapper()
        mapper.set_mapping({"supplier_id": ["supplier", "vendor"]})
        results = mapper.map_columns(["vendor"])
        assert results[0].mapped_field == "supplier_id"

    def test_empty_mapping_returns_no_match(self) -> None:
        mapper = ColumnMapper(mapping={})
        results = mapper.map_columns(["id"])
        assert results[0].mapped_field is None
