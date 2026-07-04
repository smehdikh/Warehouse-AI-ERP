"""
Excel Intelligence Engine — main orchestrator.

:class:`ExcelLoader` is the single entry-point for consuming application code.
It coordinates the full pipeline:

1. Read raw data (:class:`~excel_reader.ExcelReader`)
2. Detect active sheets (:class:`~sheet_detector.SheetDetector`)
3. Detect header rows (:class:`~header_detector.HeaderDetector`)
4. Detect column schemas (:class:`~schema_detector.SchemaDetector`)
5. Map columns to canonical fields (:class:`~column_mapper.ColumnMapper`)
6. Classify the file (:class:`~file_classifier.FileClassifier`)
7. Validate data (:class:`~validators.Validator`)
8. Score quality (:class:`~quality_score.QualityScorer`)

All errors are caught and recorded in :attr:`~models.ExcelFileResult.error_report`
so the caller always receives a complete, usable result object.
"""

from __future__ import annotations

import traceback
from pathlib import Path

from src.excel_engine.column_mapper import ColumnMapper
from src.excel_engine.excel_reader import ExcelReader, ExcelReadError, UnsupportedFormatError
from src.excel_engine.file_classifier import FileClassifier
from src.excel_engine.header_detector import HeaderDetector
from src.excel_engine.models import (
    ErrorReport,
    ExcelFileResult,
    FileClass,
    FileClassification,
    QualityScore,
    RawSheet,
    SheetResult,
)
from src.excel_engine.normalizers import normalize_header
from src.excel_engine.quality_score import QualityScorer
from src.excel_engine.schema_detector import SchemaDetector
from src.excel_engine.sheet_detector import SheetDetector, SheetSummary
from src.excel_engine.validators import ValidationRule, Validator


class ExcelLoader:
    """
    High-level orchestrator for the Excel Intelligence Engine pipeline.

    All sub-components can be injected for customisation or testing.

    Example::

        result = ExcelLoader().load(Path("report.xlsx"))
        print(result.quality_score.overall)
    """

    def __init__(
        self,
        reader: ExcelReader | None = None,
        sheet_detector: SheetDetector | None = None,
        header_detector: HeaderDetector | None = None,
        schema_detector: SchemaDetector | None = None,
        column_mapper: ColumnMapper | None = None,
        file_classifier: FileClassifier | None = None,
        validator: Validator | None = None,
        quality_scorer: QualityScorer | None = None,
        validation_rules: list[ValidationRule] | None = None,
        column_mapping: dict[str, list[str]] | None = None,
    ) -> None:
        self._reader = reader or ExcelReader()
        self._sheet_detector = sheet_detector or SheetDetector()
        self._header_detector = header_detector or HeaderDetector()
        self._schema_detector = schema_detector or SchemaDetector()
        self._column_mapper = column_mapper or ColumnMapper(mapping=column_mapping or {})
        self._file_classifier = file_classifier or FileClassifier()
        self._quality_scorer = quality_scorer or QualityScorer()
        self._validator = validator or Validator(rules=validation_rules or [])

    def load(self, path: Path) -> ExcelFileResult:
        """
        Execute the full pipeline and return a standard result.

        Args:
            path: Path to an Excel file (.xlsx, .xlsm, or .xls).

        Returns:
            :class:`~models.ExcelFileResult` — always returned, even on error.
            Errors are recorded in :attr:`~models.ExcelFileResult.error_report`.
        """
        path = Path(path)
        errors: list[ErrorReport] = []

        result = ExcelFileResult(
            file_path=str(path),
            file_name=path.name,
            file_extension=path.suffix.lower(),
            file_size_bytes=path.stat().st_size if path.exists() else 0,
        )

        # ------------------------------------------------------------------
        # Stage 1: Read raw data
        # ------------------------------------------------------------------
        try:
            raw_sheets = self._reader.read(path)
        except (UnsupportedFormatError, ExcelReadError) as exc:
            errors.append(ErrorReport(stage="read", message=str(exc)))
            result.error_report = errors
            return result
        except Exception as exc:
            errors.append(
                ErrorReport(
                    stage="read",
                    message=f"Unexpected error: {exc}",
                    details={"traceback": traceback.format_exc()},
                )
            )
            result.error_report = errors
            return result

        result.total_sheets = len(raw_sheets)

        # ------------------------------------------------------------------
        # Stage 2: Detect active sheets
        # ------------------------------------------------------------------
        sheet_summaries = self._detect_sheets(raw_sheets, errors)

        # ------------------------------------------------------------------
        # Stage 3 – 5: Per-sheet processing
        # ------------------------------------------------------------------
        sheet_results = self._process_sheets(raw_sheets, sheet_summaries, errors)

        result.sheet_results = sheet_results
        result.active_sheet_count = sum(1 for s in sheet_results if s.is_active)

        # ------------------------------------------------------------------
        # Stage 6: Classify file
        # ------------------------------------------------------------------
        try:
            result.classification = self._file_classifier.classify(sheet_results)
        except Exception as exc:
            errors.append(ErrorReport(stage="classify", message=str(exc)))
            result.classification = FileClassification(label=FileClass.UNKNOWN, confidence=0.0)

        # ------------------------------------------------------------------
        # Stage 7: Validate
        # ------------------------------------------------------------------
        try:
            all_issues = []
            for raw_sheet, sheet_result in self._safe_zip(raw_sheets, sheet_results, "validate", errors):
                if not sheet_result.is_active or sheet_result.header_row_index is None:
                    continue
                data_rows = raw_sheet.rows[sheet_result.header_row_index + 1 :]
                issues = self._validator.validate(raw_sheet.name, sheet_result.columns, data_rows)
                all_issues.extend(issues)
            result.validation_issues = all_issues
        except Exception as exc:
            errors.append(ErrorReport(stage="validate", message=str(exc)))

        # ------------------------------------------------------------------
        # Stage 8: Quality score
        # ------------------------------------------------------------------
        try:
            result.quality_score = self._quality_scorer.score(sheet_results, result.validation_issues)
        except Exception as exc:
            errors.append(ErrorReport(stage="quality_score", message=str(exc)))
            result.quality_score = QualityScore()

        result.error_report = errors
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_sheets(
        self,
        raw_sheets: list[RawSheet],
        errors: list[ErrorReport],
    ) -> list[SheetSummary]:
        """Run sheet detection; on failure return inactive fallback summaries."""
        try:
            summaries = self._sheet_detector.detect(raw_sheets)
            if len(summaries) != len(raw_sheets):
                errors.append(
                    ErrorReport(
                        stage="detect_sheets",
                        message=(
                            f"SheetDetector returned {len(summaries)} summaries "
                            f"for {len(raw_sheets)} sheets; padding with inactive entries."
                        ),
                    )
                )
                # Pad or truncate so lengths always match.
                while len(summaries) < len(raw_sheets):
                    idx = len(summaries)
                    rs = raw_sheets[idx]
                    summaries.append(
                        SheetSummary(
                            name=rs.name,
                            index=rs.index,
                            is_active=False,
                            row_count=rs.row_count,
                            col_count=rs.col_count,
                            non_empty_row_count=0,
                            is_hidden=rs.is_hidden,
                            signals=["length_mismatch"],
                        )
                    )
                summaries = summaries[: len(raw_sheets)]
            return summaries
        except Exception as exc:
            errors.append(ErrorReport(stage="detect_sheets", message=str(exc)))
            # Build fully-inactive fallback summaries so every raw_sheet still
            # gets a SheetResult; downstream stages are skipped via is_active=False.
            return [
                SheetSummary(
                    name=rs.name,
                    index=rs.index,
                    is_active=False,
                    row_count=rs.row_count,
                    col_count=rs.col_count,
                    non_empty_row_count=0,
                    is_hidden=rs.is_hidden,
                    signals=["detect_sheets_failed"],
                )
                for rs in raw_sheets
            ]

    def _process_sheets(
        self,
        raw_sheets: list[RawSheet],
        sheet_summaries: list[SheetSummary],
        errors: list[ErrorReport],
    ) -> list[SheetResult]:
        """Run per-sheet header/schema/mapping pipeline."""
        sheet_results: list[SheetResult] = []
        for raw_sheet, summary in zip(raw_sheets, sheet_summaries, strict=True):
            sheet_result = SheetResult(
                name=raw_sheet.name,
                index=raw_sheet.index,
                is_active=summary.is_active,
                row_count=raw_sheet.row_count,
                col_count=summary.col_count,
            )

            if not summary.is_active or not raw_sheet.rows:
                sheet_results.append(sheet_result)
                continue

            # Header detection
            try:
                header_res = self._header_detector.detect(raw_sheet.rows)
                sheet_result.header_row_index = header_res.header_row_index

                if header_res.header_row_index is not None:
                    raw_headers = HeaderDetector.extract_headers(raw_sheet.rows, header_res.header_row_index)
                    data_rows = raw_sheet.rows[header_res.header_row_index + 1 :]
                else:
                    raw_headers = []
                    data_rows = raw_sheet.rows

                sheet_result.data_row_count = len(data_rows)

            except Exception as exc:
                errors.append(
                    ErrorReport(
                        stage="detect_headers",
                        message=str(exc),
                        details={"sheet": raw_sheet.name},
                    )
                )
                sheet_results.append(sheet_result)
                continue

            if not raw_headers:
                sheet_results.append(sheet_result)
                continue

            # Schema detection
            try:
                norm_headers = [normalize_header(h) for h in raw_headers]
                column_schemas = self._schema_detector.detect_sheet(raw_headers, norm_headers, data_rows)
            except Exception as exc:
                errors.append(
                    ErrorReport(
                        stage="detect_schema",
                        message=str(exc),
                        details={"sheet": raw_sheet.name},
                    )
                )
                sheet_results.append(sheet_result)
                continue

            # Column mapping
            try:
                mapping_results = self._column_mapper.map_columns(raw_headers)
                if len(mapping_results) == len(column_schemas):
                    for schema, mapping in zip(column_schemas, mapping_results, strict=True):
                        schema.mapped_field = mapping.mapped_field
                else:
                    errors.append(
                        ErrorReport(
                            stage="map_columns",
                            message=(
                                f"ColumnMapper returned {len(mapping_results)} results "
                                f"for {len(column_schemas)} schemas in sheet '{raw_sheet.name}'"
                            ),
                        )
                    )
            except Exception as exc:
                errors.append(
                    ErrorReport(
                        stage="map_columns",
                        message=str(exc),
                        details={"sheet": raw_sheet.name},
                    )
                )

            sheet_result.columns = column_schemas
            sheet_results.append(sheet_result)

        return sheet_results

    @staticmethod
    def _safe_zip(
        a: list[RawSheet],
        b: list[SheetResult],
        stage: str,
        errors: list[ErrorReport],
    ):
        """Zip two parallel lists and flag any length mismatch as an error."""
        if len(a) != len(b):
            errors.append(
                ErrorReport(
                    stage=stage,
                    message=(
                        f"Length mismatch in stage '{stage}': "
                        f"{len(a)} raw sheets vs {len(b)} results; "
                        "truncating to shorter list."
                    ),
                )
            )
        return zip(a, b, strict=False)
