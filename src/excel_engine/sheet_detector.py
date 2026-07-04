"""Worksheet detector — identifies which sheets contain usable tabular data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from src.excel_engine.models import CellValue, RawSheet


@dataclass
class SheetSummary:
    """Lightweight summary produced by :class:`SheetDetector`."""

    name: str
    index: int
    is_active: bool
    row_count: int
    col_count: int
    non_empty_row_count: int
    is_hidden: bool
    signals: list[str] = field(default_factory=list)


class SheetDetector:
    """
    Analyse a list of :class:`RawSheet` objects and decide which sheets
    contain useful data.

    A sheet is marked *active* when:
    - It is not hidden (configurable).
    - It has at least ``min_data_rows`` non-empty rows.
    - It has at least ``min_cols`` columns in its widest non-empty row.
    """

    def __init__(
        self,
        min_data_rows: int = 1,
        min_cols: int = 1,
        include_hidden: bool = False,
    ) -> None:
        self.min_data_rows = min_data_rows
        self.min_cols = min_cols
        self.include_hidden = include_hidden

    def detect(self, sheets: list[RawSheet]) -> list[SheetSummary]:
        """
        Analyse sheets and return a :class:`SheetSummary` for each one.

        Args:
            sheets: Raw sheets as returned by :class:`~excel_reader.ExcelReader`.

        Returns:
            List of summaries in the same order as ``sheets``.
        """
        return [self._analyse(sheet) for sheet in sheets]

    def _analyse(self, sheet: RawSheet) -> SheetSummary:
        non_empty_rows = [r for r in sheet.rows if self._row_has_data(r)]
        max_cols = max((len(r) for r in non_empty_rows), default=0)
        signals: list[str] = []
        is_active = True

        if sheet.is_hidden and not self.include_hidden:
            is_active = False
            signals.append("hidden_sheet")

        if len(non_empty_rows) < self.min_data_rows:
            is_active = False
            signals.append("too_few_rows")

        if max_cols < self.min_cols:
            is_active = False
            signals.append("too_few_columns")

        return SheetSummary(
            name=sheet.name,
            index=sheet.index,
            is_active=is_active,
            row_count=sheet.row_count,
            col_count=max_cols,
            non_empty_row_count=len(non_empty_rows),
            is_hidden=sheet.is_hidden,
            signals=signals,
        )

    @staticmethod
    def _row_has_data(row: Sequence[CellValue]) -> bool:
        """Return True if at least one cell in the row is non-null and non-empty."""
        return any(v is not None and str(v).strip() != "" for v in row)
