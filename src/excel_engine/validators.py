"""Validators — pluggable, rule-based data validation for Excel sheets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.excel_engine.models import CellValue, ColumnSchema, ColumnType, Severity, ValidationIssue

# ---------------------------------------------------------------------------
# Base rule interface
# ---------------------------------------------------------------------------


class ValidationRule(ABC):
    """Abstract base class for all validation rules."""

    code: str = "BASE"

    @abstractmethod
    def validate(
        self,
        sheet_name: str,
        columns: list[ColumnSchema],
        data_rows: list[list[CellValue]],
    ) -> list[ValidationIssue]:
        """
        Run this rule against the given sheet data.

        Args:
            sheet_name: Name of the worksheet being validated.
            columns: Column schemas as detected by :class:`~schema_detector.SchemaDetector`.
            data_rows: Data rows (below the header) as raw cell values.

        Returns:
            List of :class:`~models.ValidationIssue` found, possibly empty.
        """


# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------


class RequiredFieldsRule(ValidationRule):
    """Flag cells that are null in columns designated as required."""

    code = "REQUIRED_FIELD"

    def __init__(self, required_fields: list[str]) -> None:
        self.required_fields = set(required_fields)

    def validate(
        self,
        sheet_name: str,
        columns: list[ColumnSchema],
        data_rows: list[list[CellValue]],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        required_cols = [
            c for c in columns if c.normalized_name in self.required_fields or c.raw_name in self.required_fields
        ]

        for col in required_cols:
            for row_idx, row in enumerate(data_rows):
                val = row[col.index] if col.index < len(row) else None
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    issues.append(
                        ValidationIssue(
                            severity=Severity.ERROR,
                            sheet_name=sheet_name,
                            row_index=row_idx,
                            column_name=col.raw_name,
                            column_index=col.index,
                            message=f"Required field '{col.raw_name}' is empty at row {row_idx}.",
                            code=self.code,
                        )
                    )
        return issues


class TypeConsistencyRule(ValidationRule):
    """Warn when a cell value does not match the column's detected type."""

    code = "TYPE_MISMATCH"

    def validate(
        self,
        sheet_name: str,
        columns: list[ColumnSchema],
        data_rows: list[list[CellValue]],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for col in columns:
            if col.detected_type in {ColumnType.UNKNOWN, ColumnType.MIXED, ColumnType.EMPTY}:
                continue
            expected_py = _COLUMN_TYPE_TO_PYTHON.get(col.detected_type)
            if expected_py is None:
                continue
            for row_idx, row in enumerate(data_rows):
                val = row[col.index] if col.index < len(row) else None
                if val is None:
                    continue
                if not isinstance(val, expected_py):
                    issues.append(
                        ValidationIssue(
                            severity=Severity.WARNING,
                            sheet_name=sheet_name,
                            row_index=row_idx,
                            column_name=col.raw_name,
                            column_index=col.index,
                            message=(
                                f"Column '{col.raw_name}' expects {col.detected_type.value} "
                                f"but got {type(val).__name__!r} at row {row_idx}."
                            ),
                            code=self.code,
                            context={"expected": col.detected_type.value, "actual_type": type(val).__name__},
                        )
                    )
        return issues


class DuplicateRowRule(ValidationRule):
    """Detect duplicate rows across specified key columns."""

    code = "DUPLICATE_ROW"

    def __init__(self, key_columns: list[str] | None = None) -> None:
        """
        Args:
            key_columns: Normalised or raw column names to use as the
                composite key.  When *None*, all columns are used.
        """
        self.key_columns = key_columns

    def validate(
        self,
        sheet_name: str,
        columns: list[ColumnSchema],
        data_rows: list[list[CellValue]],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if self.key_columns:
            key_col_indices = [
                c.index for c in columns if c.normalized_name in self.key_columns or c.raw_name in self.key_columns
            ]
        else:
            key_col_indices = [c.index for c in columns]

        if not key_col_indices:
            return issues

        seen: dict[tuple[Any, ...], int] = {}
        for row_idx, row in enumerate(data_rows):
            key = tuple(row[i] if i < len(row) else None for i in key_col_indices)
            if key in seen:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        sheet_name=sheet_name,
                        row_index=row_idx,
                        message=f"Duplicate row at index {row_idx} (first seen at {seen[key]}).",
                        code=self.code,
                        context={"first_occurrence": seen[key], "key": list(key)},
                    )
                )
            else:
                seen[key] = row_idx

        return issues


class ColumnCountConsistencyRule(ValidationRule):
    """Warn when a data row has a different number of cells than the header."""

    code = "COLUMN_COUNT_MISMATCH"

    def validate(
        self,
        sheet_name: str,
        columns: list[ColumnSchema],
        data_rows: list[list[CellValue]],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        expected = len(columns)
        for row_idx, row in enumerate(data_rows):
            if len(row) != expected:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        sheet_name=sheet_name,
                        row_index=row_idx,
                        message=f"Row {row_idx} has {len(row)} columns; expected {expected}.",
                        code=self.code,
                        context={"expected": expected, "actual": len(row)},
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class ValidatorConfig:
    """Configuration for :class:`Validator`."""

    rules: list[ValidationRule] = field(default_factory=list)


class Validator:
    """
    Run a configurable set of :class:`ValidationRule` objects against sheet data.

    Usage::

        validator = Validator(rules=[RequiredFieldsRule(["sku", "price"]), DuplicateRowRule()])
        issues = validator.validate(sheet_name, columns, data_rows)
    """

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self.rules: list[ValidationRule] = rules or []

    def add_rule(self, rule: ValidationRule) -> None:
        """Append a rule to the active rule set."""
        self.rules.append(rule)

    def validate(
        self,
        sheet_name: str,
        columns: list[ColumnSchema],
        data_rows: list[list[CellValue]],
    ) -> list[ValidationIssue]:
        """
        Run all rules and collect issues.

        Returns:
            Flat list of all :class:`~models.ValidationIssue` found.
        """
        issues: list[ValidationIssue] = []
        for rule in self.rules:
            issues.extend(rule.validate(sheet_name, columns, data_rows))
        return issues


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

import datetime  # noqa: E402

_COLUMN_TYPE_TO_PYTHON: dict[ColumnType, type | tuple[type, ...]] = {
    ColumnType.STRING: str,
    ColumnType.INTEGER: (int, bool),
    ColumnType.FLOAT: (float, int, bool),
    ColumnType.DATE: datetime.datetime,
    ColumnType.BOOLEAN: bool,
}
