"""Excel Intelligence Engine — reusable infrastructure for reading and analysing Excel files."""

from src.excel_engine.loader import ExcelLoader
from src.excel_engine.models import ExcelFileResult

__all__ = ["ExcelLoader", "ExcelFileResult"]
