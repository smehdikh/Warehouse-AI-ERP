"""Tests for header_detector.HeaderDetector."""

from __future__ import annotations

from src.excel_engine.header_detector import HeaderDetector
from src.excel_engine.models import CellValue


def rows(*args: list[CellValue]) -> list[list[CellValue]]:
    return list(args)


class TestHeaderDetector:
    def setup_method(self) -> None:
        self.detector = HeaderDetector()

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def test_first_row_all_strings(self) -> None:
        data = rows(["ID", "Name", "Price"], [1, "A", 9.99])
        result = self.detector.detect(data)
        assert result.header_row_index == 0
        assert result.confidence >= 0.9

    def test_blank_rows_before_header(self) -> None:
        data = rows(
            [None, None, None],
            [None, None, None],
            ["SKU", "Desc", "Qty"],
            ["A001", "Bolt", 10],
        )
        result = self.detector.detect(data)
        assert result.header_row_index == 2

    def test_empty_sheet_returns_none(self) -> None:
        result = self.detector.detect([])
        assert result.header_row_index is None
        assert result.confidence == 0.0
        assert "empty_sheet" in result.signals

    def test_no_data_returns_none(self) -> None:
        data = rows([None, None], [None, None])
        result = self.detector.detect(data)
        assert result.header_row_index is None

    def test_majority_string_row(self) -> None:
        # 3/4 strings — above default 0.6 ratio
        data = rows(["Name", "Code", "Qty", 42], [1, "A", 5, 100])
        result = self.detector.detect(data)
        assert result.header_row_index == 0

    def test_confidence_is_between_0_and_1(self) -> None:
        data = rows(["A", "B"], [1, 2])
        result = self.detector.detect(data)
        assert 0.0 <= result.confidence <= 1.0

    def test_signals_list_populated(self) -> None:
        data = rows(["A", "B"], [1, 2])
        result = self.detector.detect(data)
        assert len(result.signals) > 0

    def test_max_scan_rows_respected(self) -> None:
        detector = HeaderDetector(max_scan_rows=2)
        data = [
            [1, 2, 3],  # row 0: numeric
            [4, 5, 6],  # row 1: numeric
            ["A", "B", "C"],  # row 2: header but beyond scan limit
            [7, 8, 9],
        ]
        result = detector.detect(data)
        # Header at row 2 should not be detected within limit of 2
        assert result.header_row_index != 2 or result.confidence < 0.5

    # ------------------------------------------------------------------
    # extract_headers
    # ------------------------------------------------------------------

    def test_extract_headers_returns_labels(self) -> None:
        data = rows(["ID", "Name", "Price"], [1, "A", 9.99])
        headers = HeaderDetector.extract_headers(data, 0)
        assert headers == ["ID", "Name", "Price"]

    def test_extract_headers_fills_empty_with_placeholder(self) -> None:
        data = rows(["ID", None, "Price"], [1, "X", 2.0])
        headers = HeaderDetector.extract_headers(data, 0)
        assert headers[1] == "col_1"

    def test_extract_headers_out_of_bounds(self) -> None:
        data = rows(["A", "B"])
        headers = HeaderDetector.extract_headers(data, 99)
        assert headers == []
