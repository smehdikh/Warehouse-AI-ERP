"""Schema detector — infers the data type and statistics of each column."""

from __future__ import annotations

import datetime
import statistics
from dataclasses import dataclass, field
from typing import Any

from src.excel_engine.models import CellValue, ColumnSchema, ColumnType


@dataclass
class ColumnStats:
    """Raw statistics gathered before type inference."""

    total: int = 0
    null_count: int = 0
    int_count: int = 0
    float_count: int = 0
    str_count: int = 0
    bool_count: int = 0
    date_count: int = 0
    sample: list[CellValue] = field(default_factory=list)
    unique_values: set[Any] = field(default_factory=set)

    @property
    def non_null(self) -> int:
        return self.total - self.null_count


class SchemaDetector:
    """
    Heuristic type detector for spreadsheet columns.

    For each column (supplied as a flat list of cell values), it:

    - Counts null / non-null cells.
    - Tallies occurrences of each Python primitive type.
    - Infers a dominant :class:`~models.ColumnType`.
    - Builds a :class:`~models.ColumnSchema` with completeness stats.

    The ``dominance_threshold`` controls how large a fraction of non-null
    cells must belong to a single type before it is declared dominant
    (default: 0.80).
    """

    def __init__(
        self,
        dominance_threshold: float = 0.80,
        max_sample: int = 10,
        max_unique_scan: int = 1000,
    ) -> None:
        self.dominance_threshold = dominance_threshold
        self.max_sample = max_sample
        self.max_unique_scan = max_unique_scan

    def detect_column(
        self,
        index: int,
        raw_name: str,
        normalized_name: str,
        values: list[CellValue],
    ) -> ColumnSchema:
        """
        Infer the schema for a single column.

        Args:
            index: 0-based column position.
            raw_name: Original header label.
            normalized_name: Normalised header label.
            values: All data values for this column (excluding the header cell).

        Returns:
            A populated :class:`~models.ColumnSchema`.
        """
        stats = self._gather_stats(values)
        col_type = self._infer_type(stats)
        null_rate = stats.null_count / stats.total if stats.total else 0.0

        return ColumnSchema(
            index=index,
            raw_name=raw_name,
            normalized_name=normalized_name,
            detected_type=col_type,
            null_count=stats.null_count,
            total_count=stats.total,
            unique_count=len(stats.unique_values),
            null_rate=round(null_rate, 4),
            sample_values=stats.sample,
        )

    def detect_sheet(
        self,
        raw_names: list[str],
        normalized_names: list[str],
        data_rows: list[list[CellValue]],
    ) -> list[ColumnSchema]:
        """
        Infer schemas for all columns in a sheet at once.

        Args:
            raw_names: Header labels as read from the file.
            normalized_names: Normalised versions of ``raw_names``.
            data_rows: Rows *below* the header row.

        Returns:
            One :class:`~models.ColumnSchema` per column.
        """
        if not raw_names:
            return []

        # Transpose rows → columns
        num_cols = len(raw_names)
        columns: list[list[CellValue]] = [[] for _ in range(num_cols)]
        for row in data_rows:
            for col_idx in range(num_cols):
                columns[col_idx].append(row[col_idx] if col_idx < len(row) else None)

        return [self.detect_column(i, raw_names[i], normalized_names[i], columns[i]) for i in range(num_cols)]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _gather_stats(self, values: list[CellValue]) -> ColumnStats:
        stats = ColumnStats(total=len(values))
        for v in values:
            if v is None or (isinstance(v, str) and v.strip() == ""):
                stats.null_count += 1
                continue
            # Type tally
            if isinstance(v, bool):
                stats.bool_count += 1
            elif isinstance(v, int):
                stats.int_count += 1
            elif isinstance(v, float):
                stats.float_count += 1
            elif isinstance(v, datetime.datetime):
                stats.date_count += 1
            else:
                stats.str_count += 1

            # Unique values (capped to avoid memory issues)
            if len(stats.unique_values) < self.max_unique_scan:
                stats.unique_values.add(v)

            # Sample (first N non-null)
            if len(stats.sample) < self.max_sample:
                stats.sample.append(v)

        return stats

    def _infer_type(self, stats: ColumnStats) -> ColumnType:
        if stats.total == 0 or stats.non_null == 0:
            return ColumnType.EMPTY

        nn = stats.non_null
        threshold = self.dominance_threshold

        if stats.bool_count / nn >= threshold:
            return ColumnType.BOOLEAN
        if stats.date_count / nn >= threshold:
            return ColumnType.DATE
        if stats.int_count / nn >= threshold:
            return ColumnType.INTEGER
        if (stats.int_count + stats.float_count) / nn >= threshold:
            return ColumnType.FLOAT
        if stats.str_count / nn >= threshold:
            return ColumnType.STRING

        # Multiple types present but no dominant one
        type_counts = [
            stats.int_count,
            stats.float_count,
            stats.str_count,
            stats.bool_count,
            stats.date_count,
        ]
        if statistics.stdev(type_counts) > 0:
            return ColumnType.MIXED

        return ColumnType.UNKNOWN
