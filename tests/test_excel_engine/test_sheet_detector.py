"""Tests for sheet_detector.SheetDetector."""

from __future__ import annotations

from src.excel_engine.models import RawSheet
from src.excel_engine.sheet_detector import SheetDetector


def _make_sheet(
    name: str = "Sheet1",
    index: int = 0,
    rows: list[list[object]] | None = None,
    is_hidden: bool = False,
) -> RawSheet:
    return RawSheet(name=name, index=index, rows=rows or [], is_hidden=is_hidden)


class TestSheetDetector:
    def setup_method(self) -> None:
        self.detector = SheetDetector()

    def test_single_sheet_with_data_is_active(self) -> None:
        sheet = _make_sheet(rows=[["ID", "Name"], [1, "A"]])
        result = self.detector.detect([sheet])
        assert result[0].is_active is True

    def test_empty_sheet_is_inactive(self) -> None:
        sheet = _make_sheet(rows=[])
        result = self.detector.detect([sheet])
        assert result[0].is_active is False

    def test_all_null_rows_is_inactive(self) -> None:
        sheet = _make_sheet(rows=[[None, None], [None, None]])
        result = self.detector.detect([sheet])
        assert result[0].is_active is False

    def test_hidden_sheet_is_inactive_by_default(self) -> None:
        sheet = _make_sheet(rows=[["ID"], [1]], is_hidden=True)
        result = self.detector.detect([sheet])
        assert result[0].is_active is False
        assert "hidden_sheet" in result[0].signals

    def test_hidden_sheet_active_when_include_hidden(self) -> None:
        detector = SheetDetector(include_hidden=True)
        sheet = _make_sheet(rows=[["ID"], [1]], is_hidden=True)
        result = detector.detect([sheet])
        assert result[0].is_active is True

    def test_multi_sheet_detection(self) -> None:
        sheets = [
            _make_sheet("Data", 0, [["A", "B"], [1, 2]]),
            _make_sheet("Empty", 1, []),
            _make_sheet("More", 2, [["X"], [10]]),
        ]
        result = self.detector.detect(sheets)
        assert result[0].is_active is True
        assert result[1].is_active is False
        assert result[2].is_active is True

    def test_row_count_and_col_count(self) -> None:
        sheet = _make_sheet(rows=[["A", "B", "C"], [1, 2, 3], [4, 5, 6]])
        result = self.detector.detect([sheet])
        assert result[0].row_count == 3
        assert result[0].col_count == 3
        assert result[0].non_empty_row_count == 3

    def test_min_cols_threshold(self) -> None:
        detector = SheetDetector(min_cols=3)
        sheet = _make_sheet(rows=[["A", "B"], [1, 2]])
        result = detector.detect([sheet])
        assert result[0].is_active is False
        assert "too_few_columns" in result[0].signals

    def test_signals_populated_for_inactive(self) -> None:
        sheet = _make_sheet(rows=[])
        result = self.detector.detect([sheet])
        assert len(result[0].signals) > 0

    def test_preserves_sheet_order(self) -> None:
        sheets = [_make_sheet(f"S{i}", i, [["x"], [i]]) for i in range(5)]
        result = self.detector.detect(sheets)
        assert [r.index for r in result] == list(range(5))
