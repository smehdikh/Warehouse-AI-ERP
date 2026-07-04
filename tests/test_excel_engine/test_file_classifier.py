"""Tests for file_classifier.FileClassifier."""

from __future__ import annotations

from src.excel_engine.file_classifier import FileClassifier
from src.excel_engine.models import ColumnSchema, ColumnType, FileClass, SheetResult


def _make_sheet(
    name: str = "Sheet1",
    index: int = 0,
    is_active: bool = True,
    row_count: int = 10,
    col_count: int = 3,
    data_row_count: int = 8,
    header_row_index: int | None = 0,
    col_types: list[ColumnType] | None = None,
) -> SheetResult:
    cols = [
        ColumnSchema(
            index=i,
            raw_name=f"col_{i}",
            normalized_name=f"col_{i}",
            detected_type=t,
        )
        for i, t in enumerate(col_types or [ColumnType.STRING] * col_count)
    ]
    return SheetResult(
        name=name,
        index=index,
        is_active=is_active,
        row_count=row_count,
        col_count=col_count,
        data_row_count=data_row_count,
        header_row_index=header_row_index,
        columns=cols,
    )


class TestFileClassifier:
    def setup_method(self) -> None:
        self.classifier = FileClassifier()

    def test_empty_file_classified_as_empty(self) -> None:
        result = self.classifier.classify([])
        assert result.label == FileClass.EMPTY

    def test_no_active_sheets_is_empty(self) -> None:
        sheet = _make_sheet(is_active=False)
        result = self.classifier.classify([sheet])
        assert result.label == FileClass.EMPTY

    def test_single_tabular_sheet(self) -> None:
        sheet = _make_sheet()
        result = self.classifier.classify([sheet])
        assert result.label == FileClass.TABULAR
        assert result.confidence >= 0.8

    def test_multi_tabular_sheets(self) -> None:
        sheets = [_make_sheet(f"S{i}", i) for i in range(3)]
        result = self.classifier.classify(sheets)
        assert result.label == FileClass.MULTI_TABULAR

    def test_matrix_file(self) -> None:
        # First col string, rest numeric
        col_types = [ColumnType.STRING, ColumnType.FLOAT, ColumnType.FLOAT]
        sheet = _make_sheet(col_types=col_types, header_row_index=None)
        result = self.classifier.classify([sheet])
        assert result.label == FileClass.MATRIX

    def test_sparse_is_dashboard(self) -> None:
        # density = 2/50 = 0.04 < 0.3 and row_count > 10
        sheet = _make_sheet(row_count=50, data_row_count=2, col_types=[ColumnType.STRING, ColumnType.STRING])
        result = self.classifier.classify([sheet])
        assert result.label == FileClass.DASHBOARD

    def test_confidence_in_range(self) -> None:
        sheet = _make_sheet()
        result = self.classifier.classify([sheet])
        assert 0.0 <= result.confidence <= 1.0

    def test_signals_populated(self) -> None:
        sheet = _make_sheet()
        result = self.classifier.classify([sheet])
        assert len(result.signals) > 0

    def test_mixed_active_sheets(self) -> None:
        tabular = _make_sheet("T", 0)
        non_tabular = _make_sheet("N", 1, col_count=1, col_types=[ColumnType.STRING])
        result = self.classifier.classify([tabular, non_tabular])
        # Not all tabular → mixed
        assert result.label == FileClass.MIXED
