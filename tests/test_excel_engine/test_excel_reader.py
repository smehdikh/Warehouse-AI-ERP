"""Tests for excel_reader.ExcelReader."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_engine.excel_reader import ExcelReader, ExcelReadError, UnsupportedFormatError


class TestExcelReader:
    def setup_method(self) -> None:
        self.reader = ExcelReader()

    # ------------------------------------------------------------------
    # Happy-path
    # ------------------------------------------------------------------

    def test_read_xlsx_returns_sheets(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        assert len(sheets) == 1

    def test_read_xlsx_sheet_name(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        assert sheets[0].name == "Sheet1"

    def test_read_xlsx_row_count(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        assert sheets[0].row_count == 4  # 1 header + 3 data

    def test_read_xlsx_col_count(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        assert sheets[0].col_count == 4

    def test_read_xlsx_header_values(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        header_row = sheets[0].rows[0]
        assert header_row == ["ID", "Name", "Price", "Quantity"]

    def test_read_xlsx_numeric_cells(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        id_cell = sheets[0].rows[1][0]
        assert id_cell == 1
        assert isinstance(id_cell, int)

    def test_read_xlsx_float_cells(self, simple_xlsx: Path) -> None:
        sheets = self.reader.read(simple_xlsx)
        price = sheets[0].rows[1][2]
        assert price == 9.99
        assert isinstance(price, float)

    def test_read_multi_sheet(self, multi_sheet_xlsx: Path) -> None:
        sheets = self.reader.read(multi_sheet_xlsx)
        assert len(sheets) == 3
        names = [s.name for s in sheets]
        assert "Products" in names
        assert "Suppliers" in names
        assert "EmptySheet" in names

    def test_read_empty_xlsx(self, empty_xlsx: Path) -> None:
        sheets = self.reader.read(empty_xlsx)
        assert len(sheets) == 1
        assert sheets[0].row_count == 0

    def test_sheet_index_is_sequential(self, multi_sheet_xlsx: Path) -> None:
        sheets = self.reader.read(multi_sheet_xlsx)
        for i, sheet in enumerate(sheets):
            assert sheet.index == i

    def test_read_mixed_types(self, mixed_types_xlsx: Path) -> None:
        import datetime

        sheets = self.reader.read(mixed_types_xlsx)
        rows = sheets[0].rows
        assert isinstance(rows[1][0], str)
        assert isinstance(rows[1][2], datetime.datetime)

    # ------------------------------------------------------------------
    # Error cases
    # ------------------------------------------------------------------

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "data.csv"
        p.write_text("a,b,c")
        with pytest.raises(UnsupportedFormatError):
            self.reader.read(p)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ExcelReadError):
            self.reader.read(tmp_path / "nonexistent.xlsx")
