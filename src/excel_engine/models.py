"""Standard output models for the Excel Intelligence Engine."""

from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# Type alias for a raw cell value read from any Excel backend.
CellValue = str | int | float | datetime.datetime | bool | None


class ColumnType(StrEnum):
    """Detected data type of a column."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    BOOLEAN = "boolean"
    MIXED = "mixed"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    """Severity level of a validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FileClass(StrEnum):
    """Generic structural classification of an Excel file."""

    TABULAR = "tabular"
    MULTI_TABULAR = "multi_tabular"
    MATRIX = "matrix"
    MIXED = "mixed"
    DASHBOARD = "dashboard"
    EMPTY = "empty"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Raw (pre-processing) models
# ---------------------------------------------------------------------------


class RawSheet(BaseModel):
    """Raw worksheet data as read directly from the file backend."""

    name: str
    index: int
    rows: list[list[CellValue]]
    is_hidden: bool = False

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return max((len(r) for r in self.rows), default=0)


# ---------------------------------------------------------------------------
# Processed (post-analysis) models
# ---------------------------------------------------------------------------


class ColumnSchema(BaseModel):
    """Schema inferred for a single column."""

    index: int
    raw_name: str
    normalized_name: str
    mapped_field: str | None = None
    detected_type: ColumnType = ColumnType.UNKNOWN
    null_count: int = 0
    total_count: int = 0
    unique_count: int = 0
    null_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_values: list[CellValue] = Field(default_factory=list)


class SheetResult(BaseModel):
    """Processed analysis result for a single worksheet."""

    name: str
    index: int
    is_active: bool
    row_count: int
    col_count: int
    data_row_count: int = 0
    header_row_index: int | None = None
    columns: list[ColumnSchema] = Field(default_factory=list)
    has_merged_cells: bool = False
    has_formulas: bool = False


class ValidationIssue(BaseModel):
    """A single issue found during validation."""

    severity: Severity
    sheet_name: str
    row_index: int | None = None
    column_name: str | None = None
    column_index: int | None = None
    message: str
    code: str
    context: dict[str, Any] = Field(default_factory=dict)


class ErrorReport(BaseModel):
    """An error that occurred during any processing stage."""

    stage: str  # e.g. "read", "detect_headers", "validate"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class QualityDimension(BaseModel):
    """Score for a single quality dimension (0.0 – 1.0)."""

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class QualityScore(BaseModel):
    """Composite quality score for an Excel file."""

    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness: QualityDimension = Field(default_factory=QualityDimension)
    consistency: QualityDimension = Field(default_factory=QualityDimension)
    validity: QualityDimension = Field(default_factory=QualityDimension)
    structural: QualityDimension = Field(default_factory=QualityDimension)


class FileClassification(BaseModel):
    """Structural classification of an Excel file."""

    label: FileClass = FileClass.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)


class ExcelFileResult(BaseModel):
    """Standard output model for a fully processed Excel file."""

    file_path: str
    file_name: str
    file_extension: str
    file_size_bytes: int = 0
    total_sheets: int = 0
    sheet_results: list[SheetResult] = Field(default_factory=list)
    active_sheet_count: int = 0
    classification: FileClassification = Field(default_factory=FileClassification)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    error_report: list[ErrorReport] = Field(default_factory=list)
    quality_score: QualityScore = Field(default_factory=QualityScore)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.validation_issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.validation_issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.validation_issues if i.severity == Severity.WARNING)

    @property
    def active_sheets(self) -> list[SheetResult]:
        return [s for s in self.sheet_results if s.is_active]
