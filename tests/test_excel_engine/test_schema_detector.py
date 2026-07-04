"""Tests for schema_detector.SchemaDetector."""

from __future__ import annotations

import datetime

from src.excel_engine.models import ColumnType
from src.excel_engine.schema_detector import SchemaDetector


class TestSchemaDetector:
    def setup_method(self) -> None:
        self.detector = SchemaDetector()

    # ------------------------------------------------------------------
    # Single column detection
    # ------------------------------------------------------------------

    def test_detect_integer_column(self) -> None:
        values = [1, 2, 3, 4, 5]
        schema = self.detector.detect_column(0, "qty", "qty", values)
        assert schema.detected_type == ColumnType.INTEGER

    def test_detect_float_column(self) -> None:
        values = [1.1, 2.2, 3.3, 4.4]
        schema = self.detector.detect_column(0, "price", "price", values)
        assert schema.detected_type == ColumnType.FLOAT

    def test_detect_string_column(self) -> None:
        values = ["alpha", "beta", "gamma", "delta"]
        schema = self.detector.detect_column(0, "name", "name", values)
        assert schema.detected_type == ColumnType.STRING

    def test_detect_boolean_column(self) -> None:
        values = [True, False, True, True, False]
        schema = self.detector.detect_column(0, "active", "active", values)
        assert schema.detected_type == ColumnType.BOOLEAN

    def test_detect_date_column(self) -> None:
        dates = [datetime.datetime(2024, 1, i) for i in range(1, 6)]
        schema = self.detector.detect_column(0, "created_at", "created_at", dates)
        assert schema.detected_type == ColumnType.DATE

    def test_detect_empty_column(self) -> None:
        schema = self.detector.detect_column(0, "empty", "empty", [])
        assert schema.detected_type == ColumnType.EMPTY

    def test_detect_all_null_column(self) -> None:
        schema = self.detector.detect_column(0, "empty", "empty", [None, None, None])
        assert schema.detected_type == ColumnType.EMPTY

    def test_detect_mixed_column(self) -> None:
        values = ["a", 1, 2.5, "b", True, "c"]
        schema = self.detector.detect_column(0, "mixed", "mixed", values)
        assert schema.detected_type in {ColumnType.MIXED, ColumnType.STRING, ColumnType.UNKNOWN}

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def test_null_count(self) -> None:
        values = [1, None, 3, None, 5]
        schema = self.detector.detect_column(0, "x", "x", values)
        assert schema.null_count == 2
        assert schema.total_count == 5

    def test_null_rate(self) -> None:
        values = [1, None, None, None, 5]
        schema = self.detector.detect_column(0, "x", "x", values)
        assert schema.null_rate == pytest.approx(0.6, abs=0.01)

    def test_unique_count(self) -> None:
        values = [1, 2, 2, 3, 3, 3]
        schema = self.detector.detect_column(0, "x", "x", values)
        assert schema.unique_count == 3

    def test_sample_values_capped(self) -> None:
        detector = SchemaDetector(max_sample=3)
        values = list(range(100))
        schema = detector.detect_column(0, "x", "x", values)
        assert len(schema.sample_values) == 3

    def test_raw_and_normalized_name_preserved(self) -> None:
        schema = self.detector.detect_column(0, "Unit Price", "unit_price", [1.0])
        assert schema.raw_name == "Unit Price"
        assert schema.normalized_name == "unit_price"

    def test_index_preserved(self) -> None:
        schema = self.detector.detect_column(7, "x", "x", [1])
        assert schema.index == 7

    # ------------------------------------------------------------------
    # Sheet-level detection
    # ------------------------------------------------------------------

    def test_detect_sheet_returns_per_column_schema(self) -> None:
        raw = ["Name", "Price", "Qty"]
        norm = ["name", "price", "qty"]
        data_rows = [
            ["Alpha", 9.99, 10],
            ["Beta", 19.99, 5],
        ]
        schemas = self.detector.detect_sheet(raw, norm, data_rows)
        assert len(schemas) == 3
        assert schemas[0].detected_type == ColumnType.STRING
        assert schemas[1].detected_type == ColumnType.FLOAT
        assert schemas[2].detected_type == ColumnType.INTEGER

    def test_detect_sheet_empty_returns_empty(self) -> None:
        schemas = self.detector.detect_sheet([], [], [])
        assert schemas == []

    def test_detect_sheet_handles_short_rows(self) -> None:
        raw = ["A", "B", "C"]
        norm = ["a", "b", "c"]
        data_rows = [["x", 1], ["y"]]  # rows shorter than header
        schemas = self.detector.detect_sheet(raw, norm, data_rows)
        assert len(schemas) == 3


import pytest  # noqa: E402
