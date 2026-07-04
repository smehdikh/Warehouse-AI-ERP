"""Quality scorer — computes a multi-dimensional quality score for a processed file."""

from __future__ import annotations

from src.excel_engine.models import (
    ColumnType,
    QualityDimension,
    QualityScore,
    Severity,
    SheetResult,
    ValidationIssue,
)

# Default weights must sum to 1.0
DEFAULT_WEIGHTS: dict[str, float] = {
    "completeness": 0.35,
    "consistency": 0.25,
    "validity": 0.25,
    "structural": 0.15,
}


class QualityScorer:
    """
    Compute a :class:`~models.QualityScore` from processed sheet results and
    validation issues.

    Four dimensions are measured:

    **Completeness** — fraction of non-null cells across all active sheets.

    **Consistency** — fraction of columns whose detected type is not
    ``MIXED`` or ``UNKNOWN``.

    **Validity** — fraction of data rows that generated no *ERROR*-level
    issues.

    **Structural** — sheet-level structural quality: presence of headers,
    minimum column count, and at least some data rows.

    The overall score is a weighted average of the four dimensions.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS

    def score(
        self,
        sheet_results: list[SheetResult],
        validation_issues: list[ValidationIssue],
    ) -> QualityScore:
        """
        Compute the quality score.

        Args:
            sheet_results: Processed sheet results.
            validation_issues: All issues emitted by :class:`~validators.Validator`.

        Returns:
            A fully populated :class:`~models.QualityScore`.
        """
        active = [s for s in sheet_results if s.is_active]

        completeness = self._score_completeness(active)
        consistency = self._score_consistency(active)
        validity = self._score_validity(active, validation_issues)
        structural = self._score_structural(active)

        overall = (
            completeness.score * self.weights.get("completeness", 0.35)
            + consistency.score * self.weights.get("consistency", 0.25)
            + validity.score * self.weights.get("validity", 0.25)
            + structural.score * self.weights.get("structural", 0.15)
        )

        return QualityScore(
            overall=round(min(max(overall, 0.0), 1.0), 4),
            completeness=completeness,
            consistency=consistency,
            validity=validity,
            structural=structural,
        )

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    def _score_completeness(self, active_sheets: list[SheetResult]) -> QualityDimension:
        """Non-null cell rate across all columns in all active sheets."""
        total_cells = 0
        non_null_cells = 0

        for sheet in active_sheets:
            for col in sheet.columns:
                total_cells += col.total_count
                non_null_cells += col.total_count - col.null_count

        if total_cells == 0:
            return QualityDimension(
                score=0.0,
                weight=self.weights.get("completeness", 0.35),
                details={"total_cells": 0, "non_null_cells": 0},
            )

        score = non_null_cells / total_cells
        return QualityDimension(
            score=round(score, 4),
            weight=self.weights.get("completeness", 0.35),
            details={"total_cells": total_cells, "non_null_cells": non_null_cells},
        )

    def _score_consistency(self, active_sheets: list[SheetResult]) -> QualityDimension:
        """Fraction of columns with a clean (non-MIXED, non-UNKNOWN) type."""
        bad_types = {ColumnType.MIXED, ColumnType.UNKNOWN}
        total_cols = 0
        clean_cols = 0

        for sheet in active_sheets:
            for col in sheet.columns:
                total_cols += 1
                if col.detected_type not in bad_types:
                    clean_cols += 1

        if total_cols == 0:
            return QualityDimension(score=0.0, weight=self.weights.get("consistency", 0.25))

        score = clean_cols / total_cols
        return QualityDimension(
            score=round(score, 4),
            weight=self.weights.get("consistency", 0.25),
            details={"total_columns": total_cols, "clean_columns": clean_cols},
        )

    def _score_validity(
        self,
        active_sheets: list[SheetResult],
        issues: list[ValidationIssue],
    ) -> QualityDimension:
        """Fraction of data rows that have no ERROR-level issues."""
        total_rows = sum(s.data_row_count for s in active_sheets)
        if total_rows == 0:
            return QualityDimension(score=0.0, weight=self.weights.get("validity", 0.25))

        error_rows: set[tuple[str, int | None]] = {
            (i.sheet_name, i.row_index) for i in issues if i.severity == Severity.ERROR and i.row_index is not None
        }
        failing_rows = len(error_rows)
        score = max(0.0, (total_rows - failing_rows) / total_rows)
        return QualityDimension(
            score=round(score, 4),
            weight=self.weights.get("validity", 0.25),
            details={"total_rows": total_rows, "error_rows": failing_rows},
        )

    def _score_structural(self, active_sheets: list[SheetResult]) -> QualityDimension:
        """Structural quality: headers present, adequate columns, data present."""
        if not active_sheets:
            return QualityDimension(score=0.0, weight=self.weights.get("structural", 0.15))

        sheet_scores: list[float] = []
        for sheet in active_sheets:
            s = 0.0
            if sheet.header_row_index is not None:
                s += 0.4
            if len(sheet.columns) >= 2:
                s += 0.3
            if sheet.data_row_count >= 1:
                s += 0.3
            sheet_scores.append(s)

        score = sum(sheet_scores) / len(sheet_scores)
        return QualityDimension(
            score=round(score, 4),
            weight=self.weights.get("structural", 0.15),
            details={"sheet_count": len(active_sheets), "per_sheet_scores": sheet_scores},
        )
