"""Integration tests for loader.ExcelLoader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.excel_engine.loader import ExcelLoader
from src.excel_engine.models import FileClass, Severity
from src.excel_engine.validators import DuplicateRowRule, RequiredFieldsRule


class TestExcelLoader:
    def setup_method(self) -> None:
        self.loader = ExcelLoader()

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_load_simple_file(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        assert result.file_name == "test.xlsx"
        assert result.file_extension == ".xlsx"
        assert result.total_sheets == 1
        assert result.active_sheet_count == 1

    def test_result_has_sheet_results(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        assert len(result.sheet_results) == 1

    def test_header_detected(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        sheet = result.sheet_results[0]
        assert sheet.header_row_index == 0

    def test_columns_detected(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        sheet = result.sheet_results[0]
        assert len(sheet.columns) == 4

    def test_data_rows_counted(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        sheet = result.sheet_results[0]
        assert sheet.data_row_count == 3

    def test_quality_score_populated(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        assert result.quality_score.overall > 0.0

    def test_classification_populated(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        assert result.classification.label in {FileClass.TABULAR, FileClass.MIXED}

    def test_no_errors_for_clean_file(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        assert result.error_report == []

    def test_file_size_populated(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        assert result.file_size_bytes > 0

    def test_multi_sheet_file(self, multi_sheet_xlsx: Path) -> None:
        result = self.loader.load(multi_sheet_xlsx)
        assert result.total_sheets == 3
        assert result.active_sheet_count == 2  # EmptySheet is inactive

    def test_empty_file_classified_empty(self, empty_xlsx: Path) -> None:
        result = self.loader.load(empty_xlsx)
        assert result.classification.label == FileClass.EMPTY

    def test_blanks_before_header(self, blanks_before_header_xlsx: Path) -> None:
        result = self.loader.load(blanks_before_header_xlsx)
        sheet = result.sheet_results[0]
        assert sheet.header_row_index == 2

    # ------------------------------------------------------------------
    # Validation integration
    # ------------------------------------------------------------------

    def test_duplicate_rows_detected(self, duplicates_xlsx: Path) -> None:
        loader = ExcelLoader(validation_rules=[DuplicateRowRule()])
        result = loader.load(duplicates_xlsx)
        dup_issues = [i for i in result.validation_issues if i.code == "DUPLICATE_ROW"]
        assert len(dup_issues) >= 1

    def test_required_field_errors(self, tmp_path: Path) -> None:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"  # type: ignore[union-attr]
        ws.append(["ID", "Name"])  # type: ignore[union-attr]
        ws.append([1, None])  # Name is null  # type: ignore[union-attr]
        ws.append([2, "Beta"])  # type: ignore[union-attr]
        path = tmp_path / "required.xlsx"
        wb.save(path)

        loader = ExcelLoader(validation_rules=[RequiredFieldsRule(["name"])])
        result = loader.load(path)
        errors = [i for i in result.validation_issues if i.severity == Severity.ERROR]
        assert len(errors) >= 1

    # ------------------------------------------------------------------
    # Error handling — read failures
    # ------------------------------------------------------------------

    def test_missing_file_returns_error_report(self, tmp_path: Path) -> None:
        result = self.loader.load(tmp_path / "missing.xlsx")
        assert len(result.error_report) >= 1
        assert result.error_report[0].stage == "read"

    def test_unsupported_extension_returns_error_report(self, tmp_path: Path) -> None:
        p = tmp_path / "data.csv"
        p.write_text("a,b")
        result = self.loader.load(p)
        assert len(result.error_report) >= 1

    # ------------------------------------------------------------------
    # Error handling — per-stage failures
    # ------------------------------------------------------------------

    def test_detect_sheets_failure_records_error_and_returns_inactive_results(self, simple_xlsx: Path) -> None:
        """When SheetDetector raises, all sheet results must be inactive,
        an error must be recorded, and the loader must not crash."""
        failing_detector = MagicMock()
        failing_detector.detect.side_effect = RuntimeError("detector exploded")
        loader = ExcelLoader(sheet_detector=failing_detector)
        result = loader.load(simple_xlsx)

        # Caller receives a structurally valid result — no exception raised.
        assert result.total_sheets == 1
        # All sheets are inactive because detect_sheets failed.
        assert all(not s.is_active for s in result.sheet_results)
        # Error is surfaced in the report with the correct stage.
        assert any(e.stage == "detect_sheets" for e in result.error_report)

    def test_detect_sheets_length_mismatch_is_logged(self, simple_xlsx: Path) -> None:
        """If SheetDetector returns fewer summaries than sheets, the loader
        must pad with inactive entries and record an error — not silently drop sheets."""
        patched_detector = MagicMock()

        # Return an empty list for a file that has 1 sheet.
        patched_detector.detect.return_value = []
        loader = ExcelLoader(sheet_detector=patched_detector)
        result = loader.load(simple_xlsx)

        assert result.total_sheets == 1
        assert len(result.sheet_results) == 1
        assert not result.sheet_results[0].is_active
        assert any(e.stage == "detect_sheets" for e in result.error_report)

    def test_classifier_failure_records_error_and_returns_unknown(self, simple_xlsx: Path) -> None:
        """A crashing FileClassifier must not abort the pipeline; classification
        defaults to UNKNOWN and the error is recorded."""
        failing_classifier = MagicMock()
        failing_classifier.classify.side_effect = ValueError("classifier exploded")
        loader = ExcelLoader(file_classifier=failing_classifier)
        result = loader.load(simple_xlsx)

        assert result.classification.label == FileClass.UNKNOWN
        assert any(e.stage == "classify" for e in result.error_report)

    def test_quality_scorer_failure_records_error_and_returns_zero_score(self, simple_xlsx: Path) -> None:
        """A crashing QualityScorer must return a zero-score and record the error."""
        from src.excel_engine.models import QualityScore

        failing_scorer = MagicMock()
        failing_scorer.score.side_effect = RuntimeError("scorer exploded")
        loader = ExcelLoader(quality_scorer=failing_scorer)
        result = loader.load(simple_xlsx)

        assert result.quality_score == QualityScore()
        assert any(e.stage == "quality_score" for e in result.error_report)

    def test_validator_failure_records_error_without_crashing(self, simple_xlsx: Path) -> None:
        """A crashing Validator must not abort the pipeline; issues list stays
        empty and the error is recorded."""
        failing_validator = MagicMock()
        failing_validator.validate.side_effect = RuntimeError("validator exploded")
        loader = ExcelLoader(validator=failing_validator)
        result = loader.load(simple_xlsx)

        assert result.validation_issues == []
        assert any(e.stage == "validate" for e in result.error_report)

    # ------------------------------------------------------------------
    # Column mapping integration
    # ------------------------------------------------------------------

    def test_column_mapping_applied(self, simple_xlsx: Path) -> None:
        loader = ExcelLoader(column_mapping={"product_id": ["id"], "unit_price": ["price"]})
        result = loader.load(simple_xlsx)
        sheet = result.sheet_results[0]
        mapped = {c.mapped_field for c in sheet.columns if c.mapped_field}
        assert "product_id" in mapped
        assert "unit_price" in mapped

    # ------------------------------------------------------------------
    # Output model completeness
    # ------------------------------------------------------------------

    def test_result_properties(self, simple_xlsx: Path) -> None:
        result = self.loader.load(simple_xlsx)
        # These are Pydantic model properties, should not raise
        _ = result.has_errors
        _ = result.error_count
        _ = result.warning_count
        _ = result.active_sheets
