"""File classifier — assigns a generic structural label to an Excel file."""

from __future__ import annotations

from src.excel_engine.models import FileClass, FileClassification, SheetResult


class FileClassifier:
    """
    Classify an Excel file by its *structural* characteristics.

    Labels are defined by :class:`~models.FileClass` and are purely generic
    (no business-domain knowledge is encoded here).

    Classification rules (evaluated in priority order):

    1. **EMPTY** — no active sheets or no data rows across all active sheets.
    2. **TABULAR** — exactly one active sheet, has a header, ≥1 data row,
       and all columns have consistent headers.
    3. **MULTI_TABULAR** — multiple active sheets, each independently tabular.
    4. **MATRIX** — one active sheet whose first column looks like row labels
       (all strings) and whose remaining columns look like numeric data.
    5. **DASHBOARD** — few data rows relative to total rows (sparse content).
    6. **MIXED** — default fallback.
    """

    def classify(self, sheet_results: list[SheetResult]) -> FileClassification:
        """
        Classify the file given processed sheet results.

        Args:
            sheet_results: One :class:`~models.SheetResult` per worksheet.

        Returns:
            A :class:`~models.FileClassification` with label, confidence,
            and the signals that drove the decision.
        """
        active = [s for s in sheet_results if s.is_active]

        if not active or all(s.data_row_count == 0 for s in active):
            return FileClassification(label=FileClass.EMPTY, confidence=0.95, signals=["no_active_sheets_with_data"])

        if len(active) == 1:
            return self._classify_single(active[0])

        # Multiple active sheets
        tabular_count = sum(1 for s in active if self._is_tabular(s))
        if tabular_count == len(active):
            return FileClassification(
                label=FileClass.MULTI_TABULAR,
                confidence=0.85,
                signals=[f"{tabular_count}_tabular_sheets"],
            )

        return FileClassification(
            label=FileClass.MIXED,
            confidence=0.5,
            signals=["mixed_sheet_structures", f"{len(active)}_active_sheets"],
        )

    def _classify_single(self, sheet: SheetResult) -> FileClassification:
        signals: list[str] = []

        if self._is_matrix(sheet):
            signals.append("first_col_all_string_rest_numeric")
            return FileClassification(label=FileClass.MATRIX, confidence=0.75, signals=signals)

        if self._is_sparse(sheet):
            signals.append(f"data_density={self._density(sheet):.2f}")
            return FileClassification(label=FileClass.DASHBOARD, confidence=0.6, signals=signals)

        if self._is_tabular(sheet):
            signals.append("has_header_and_uniform_columns")
            return FileClassification(label=FileClass.TABULAR, confidence=0.9, signals=signals)

        return FileClassification(label=FileClass.MIXED, confidence=0.4, signals=["no_clear_structure"])

    # ------------------------------------------------------------------
    # Structural predicates
    # ------------------------------------------------------------------

    @staticmethod
    def _is_tabular(sheet: SheetResult) -> bool:
        return sheet.header_row_index is not None and sheet.data_row_count >= 1 and len(sheet.columns) >= 2

    @staticmethod
    def _is_matrix(sheet: SheetResult) -> bool:
        """True if the first column is all-string and the rest are mostly numeric."""
        from src.excel_engine.models import ColumnType

        if len(sheet.columns) < 2:
            return False
        first_col = sheet.columns[0]
        other_cols = sheet.columns[1:]
        numeric_types = {ColumnType.INTEGER, ColumnType.FLOAT}
        return first_col.detected_type == ColumnType.STRING and all(
            c.detected_type in numeric_types for c in other_cols
        )

    @staticmethod
    def _density(sheet: SheetResult) -> float:
        if sheet.row_count == 0:
            return 0.0
        return sheet.data_row_count / sheet.row_count

    @classmethod
    def _is_sparse(cls, sheet: SheetResult) -> bool:
        return cls._density(sheet) < 0.3 and sheet.row_count > 10
