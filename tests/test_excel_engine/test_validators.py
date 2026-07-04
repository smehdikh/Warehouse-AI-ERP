"""Tests for validators.Validator and individual rules."""

from __future__ import annotations

from src.excel_engine.models import ColumnSchema, ColumnType, Severity
from src.excel_engine.validators import (
    ColumnCountConsistencyRule,
    DuplicateRowRule,
    RequiredFieldsRule,
    TypeConsistencyRule,
    Validator,
)


def _col(index: int, raw: str, norm: str, col_type: ColumnType = ColumnType.STRING) -> ColumnSchema:
    return ColumnSchema(index=index, raw_name=raw, normalized_name=norm, detected_type=col_type)


class TestRequiredFieldsRule:
    def setup_method(self) -> None:
        self.rule = RequiredFieldsRule(required_fields=["sku", "price"])

    def test_no_nulls_returns_no_issues(self) -> None:
        cols = [_col(0, "SKU", "sku"), _col(1, "Price", "price")]
        rows = [["A001", 9.99], ["A002", 19.99]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []

    def test_null_in_required_col_raises_error(self) -> None:
        cols = [_col(0, "SKU", "sku"), _col(1, "Price", "price")]
        rows = [["A001", None], ["A002", 19.99]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR
        assert issues[0].row_index == 0
        assert issues[0].column_name == "Price"

    def test_empty_string_in_required_col(self) -> None:
        cols = [_col(0, "SKU", "sku")]
        rows = [[""], ["A002"]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert len(issues) == 1

    def test_non_required_col_nulls_ignored(self) -> None:
        cols = [_col(0, "SKU", "sku"), _col(1, "Notes", "notes")]
        rows = [["A001", None]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []


class TestTypeConsistencyRule:
    def setup_method(self) -> None:
        self.rule = TypeConsistencyRule()

    def test_consistent_integer_column_no_issues(self) -> None:
        cols = [_col(0, "Qty", "qty", ColumnType.INTEGER)]
        rows = [[1], [2], [3]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []

    def test_string_in_integer_column_warns(self) -> None:
        cols = [_col(0, "Qty", "qty", ColumnType.INTEGER)]
        rows = [[1], ["not_a_number"], [3]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert issues[0].row_index == 1

    def test_null_values_ignored(self) -> None:
        cols = [_col(0, "Qty", "qty", ColumnType.INTEGER)]
        rows = [[1], [None], [3]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []

    def test_mixed_type_column_skipped(self) -> None:
        cols = [_col(0, "Val", "val", ColumnType.MIXED)]
        rows = [["a"], [1], [2.5]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []


class TestDuplicateRowRule:
    def setup_method(self) -> None:
        self.rule = DuplicateRowRule()

    def test_no_duplicates_no_issues(self) -> None:
        cols = [_col(0, "ID", "id"), _col(1, "Name", "name")]
        rows = [[1, "A"], [2, "B"], [3, "C"]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []

    def test_duplicate_row_detected(self) -> None:
        cols = [_col(0, "ID", "id"), _col(1, "Name", "name")]
        rows = [[1, "A"], [1, "A"], [2, "B"]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert issues[0].row_index == 1

    def test_key_columns_subset(self) -> None:
        rule = DuplicateRowRule(key_columns=["id"])
        cols = [_col(0, "ID", "id"), _col(1, "Name", "name")]
        rows = [[1, "Alpha"], [1, "Beta"]]  # same id, different name
        issues = rule.validate("Sheet1", cols, rows)
        assert len(issues) == 1

    def test_multiple_duplicates_detected(self) -> None:
        cols = [_col(0, "ID", "id")]
        rows = [[1], [1], [1], [2]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert len(issues) == 2


class TestColumnCountConsistencyRule:
    def setup_method(self) -> None:
        self.rule = ColumnCountConsistencyRule()

    def test_consistent_columns_no_issues(self) -> None:
        cols = [_col(0, "A", "a"), _col(1, "B", "b")]
        rows = [[1, 2], [3, 4]]
        issues = self.rule.validate("Sheet1", cols, rows)
        assert issues == []

    def test_short_row_warned(self) -> None:
        cols = [_col(0, "A", "a"), _col(1, "B", "b"), _col(2, "C", "c")]
        rows = [[1, 2, 3], [4, 5]]  # row 1 is short
        issues = self.rule.validate("Sheet1", cols, rows)
        assert len(issues) == 1
        assert issues[0].row_index == 1


class TestValidator:
    def test_no_rules_returns_empty(self) -> None:
        v = Validator()
        cols = [_col(0, "A", "a")]
        issues = v.validate("Sheet1", cols, [[1], [2]])
        assert issues == []

    def test_multiple_rules_combined(self) -> None:
        v = Validator(rules=[RequiredFieldsRule(["a"]), DuplicateRowRule()])
        cols = [_col(0, "A", "a")]
        rows = [[None], [1], [1]]  # null + duplicate
        issues = v.validate("Sheet1", cols, rows)
        codes = {i.code for i in issues}
        assert "REQUIRED_FIELD" in codes
        assert "DUPLICATE_ROW" in codes

    def test_add_rule_dynamically(self) -> None:
        v = Validator()
        v.add_rule(RequiredFieldsRule(["x"]))
        cols = [_col(0, "X", "x")]
        issues = v.validate("Sheet1", cols, [[None]])
        assert len(issues) == 1
