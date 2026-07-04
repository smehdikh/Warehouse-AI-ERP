"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.db import database as db_module
from src.main import app


@pytest.fixture(autouse=True)
def reset_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use an in-memory DuckDB for each test and reset the singleton."""
    import duckdb

    monkeypatch.setattr(db_module, "_connection", None)

    original_connect = duckdb.connect

    def mock_connect(
        database: str = ":memory:",
        read_only: bool = False,  # noqa: ARG001
    ) -> duckdb.DuckDBPyConnection:
        return original_connect(":memory:", read_only=False)

    monkeypatch.setattr(duckdb, "connect", mock_connect)
    yield
    db_module.close_connection()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client with DB initialized."""
    from src.db.database import init_db

    init_db()
    return TestClient(app)
