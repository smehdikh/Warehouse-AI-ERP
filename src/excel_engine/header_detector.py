"""Header row detector — locates the row index that contains column names."""

from __future__ import annotations

from dataclasses import dataclass

from src.excel_engine.models import CellValue


@dataclass
class HeaderDetectionResult:
    """Result of header row detection for a single sheet."""

    header_row_index: int | None
    """0-based index of the detected header row, or *None* if not found."""

    confidence: float
    """Confidence score 0.0 – 1.0."""

    signals: list[str]
    """Human-readable signals that influenced the decision."""


class HeaderDetector:
    """
    Heuristic-based header row detector.

    Strategy (applied in order, first match wins):

    1. **All-string row** — the first row where every non-empty cell is a
       string is treated as the header.
    2. **Majority-string row** — the first row where ≥ ``string_ratio``
       fraction of non-empty cells are strings.
    3. **Fallback** — row 0 is returned with low confidence if the sheet has
       data but no clear header was found.
    4. **No data** — returns ``None`` for empty sheets.
    """

    def __init__(
        self,
        max_scan_rows: int = 20,
        string_ratio: float = 0.6,
        min_columns: int = 2,
    ) -> None:
        self.max_scan_rows = max_scan_rows
        self.string_ratio = string_ratio
        self.min_columns = min_columns

    def detect(self, rows: list[list[CellValue]]) -> HeaderDetectionResult:
        """
        Detect the header row in ``rows``.

        Args:
            rows: All rows of a worksheet (raw cell values).

        Returns:
            :class:`HeaderDetectionResult` with the detected index and metadata.
        """
        if not rows:
            return HeaderDetectionResult(header_row_index=None, confidence=0.0, signals=["empty_sheet"])

        scan_limit = min(self.max_scan_rows, len(rows))

        for idx in range(scan_limit):
            row = rows[idx]
            non_empty = [v for v in row if v is not None and str(v).strip() != ""]
            if len(non_empty) < self.min_columns:
                continue

            string_cells = [v for v in non_empty if isinstance(v, str)]
            ratio = len(string_cells) / len(non_empty)

            if ratio == 1.0:
                return HeaderDetectionResult(
                    header_row_index=idx,
                    confidence=0.95,
                    signals=["all_string_row", f"row_index={idx}"],
                )
            if ratio >= self.string_ratio:
                return HeaderDetectionResult(
                    header_row_index=idx,
                    confidence=0.6 + 0.35 * ratio,
                    signals=["majority_string_row", f"ratio={ratio:.2f}", f"row_index={idx}"],
                )

        # Fallback: first non-empty row
        for idx in range(len(rows)):
            if any(v is not None and str(v).strip() != "" for v in rows[idx]):
                return HeaderDetectionResult(
                    header_row_index=idx,
                    confidence=0.3,
                    signals=["fallback_first_nonempty", f"row_index={idx}"],
                )

        return HeaderDetectionResult(header_row_index=None, confidence=0.0, signals=["no_data_found"])

    @staticmethod
    def extract_headers(rows: list[list[CellValue]], header_row_index: int) -> list[str]:
        """
        Return the header labels from the identified header row.

        Empty / None cells are replaced with a positional placeholder
        ``"col_<n>"``.
        """
        if header_row_index >= len(rows):
            return []
        raw_headers = rows[header_row_index]
        return [str(v).strip() if (v is not None and str(v).strip()) else f"col_{i}" for i, v in enumerate(raw_headers)]
