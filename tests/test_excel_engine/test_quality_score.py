"""Tests for quality_score.QualityScorer."""

from __future__ import annotations

import pytest

from src.excel_engine.models import ColumnSchema, ColumnType, Severity, SheetResult, ValidationIssue
from src.excel_engine.quality_score import QualityScorer


def _make_col(
    index: int,
    null_count: int = 0,
    total: int = 10,
    col_type: ColumnType = ColumnType.STRING,
) -> ColumnSchema:
    return ColumnSchema(
        index=index,
        raw_name=f"col_{index}",
        normalized_name=f"col_{index}",
        detected_type=col_type,
        null_count=null_count,
        total_count=total,
        null_rate=null_count / total if total else 0.0,
    )


def _make_sheet(
    name: str = "S1",
    is_active: bool = True,
    data_row_count: int = 10,
    row_count: int = 11,
    header_row_index: int | None = 0,
    columns: list[ColumnSchema] | None = None,
) -> SheetResult:
    return SheetResult(
        name=name,
        index=0,
        is_active=is_active,
        row_count=row_count,
        col_count=len(columns) if columns else 2,
        data_row_count=data_row_count,
        header_row_index=header_row_index,
        columns=columns or [_make_col(0), _make_col(1)],
    )


class TestQualityScorer:
    def setup_method(self) -> None:
        self.scorer = QualityScorer()

    def test_overall_in_range(self) -> None:
        sheet = _make_sheet()
        score = self.scorer.score([sheet], [])
        assert 0.0 <= score.overall <= 1.0

    def test_perfect_file_high_score(self) -> None:
        cols = [_make_col(i, null_count=0, total=20, col_type=ColumnType.STRING) for i in range(3)]
        sheet = _make_sheet(data_row_count=20, row_count=21, columns=cols)
        score = self.scorer.score([sheet], [])
        assert score.overall >= 0.7

    def test_high_null_rate_lowers_completeness(self) -> None:
        cols = [_make_col(0, null_count=9, total=10)]
        sheet = _make_sheet(columns=cols)
        score = self.scorer.score([sheet], [])
        assert score.completeness.score < 0.5

    def test_mixed_type_columns_lower_consistency(self) -> None:
        cols = [_make_col(0, col_type=ColumnType.MIXED), _make_col(1, col_type=ColumnType.UNKNOWN)]
        sheet = _make_sheet(columns=cols)
        score = self.scorer.score([sheet], [])
        assert score.consistency.score == 0.0

    def test_clean_types_high_consistency(self) -> None:
        cols = [_make_col(i, col_type=ColumnType.STRING) for i in range(3)]
        sheet = _make_sheet(columns=cols)
        score = self.scorer.score([sheet], [])
        assert score.consistency.score == 1.0

    def test_error_issues_lower_validity(self) -> None:
        sheet = _make_sheet(data_row_count=10)
        issue = ValidationIssue(
            severity=Severity.ERROR,
            sheet_name="S1",
            row_index=0,
            message="error",
            code="TEST",
        )
        score = self.scorer.score([sheet], [issue])
        assert score.validity.score < 1.0

    def test_warning_only_does_not_lower_validity(self) -> None:
        sheet = _make_sheet(data_row_count=10)
        issue = ValidationIssue(
            severity=Severity.WARNING,
            sheet_name="S1",
            row_index=0,
            message="warning",
            code="TEST",
        )
        score = self.scorer.score([sheet], [issue])
        assert score.validity.score == 1.0

    def test_no_active_sheets_returns_zero(self) -> None:
        sheet = _make_sheet(is_active=False)
        score = self.scorer.score([sheet], [])
        assert score.overall == 0.0

    def test_structural_score_with_header(self) -> None:
        sheet = _make_sheet(header_row_index=0, data_row_count=5)
        score = self.scorer.score([sheet], [])
        assert score.structural.score >= 0.7

    def test_structural_score_without_header(self) -> None:
        sheet = _make_sheet(header_row_index=None)
        score = self.scorer.score([sheet], [])
        assert score.structural.score < 0.7

    def test_dimensions_have_weights(self) -> None:
        sheet = _make_sheet()
        score = self.scorer.score([sheet], [])
        assert score.completeness.weight > 0
        assert score.consistency.weight > 0
        assert score.validity.weight > 0
        assert score.structural.weight > 0

    def test_custom_weights(self) -> None:
        scorer = QualityScorer(weights={"completeness": 1.0, "consistency": 0.0, "validity": 0.0, "structural": 0.0})
        cols = [_make_col(0, null_count=0, total=10)]
        sheet = _make_sheet(columns=cols)
        score = scorer.score([sheet], [])
        assert score.overall == pytest.approx(score.completeness.score, abs=0.01)
