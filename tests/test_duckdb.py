"""Tests verifying DuckDB configuration and connectivity."""

import duckdb


def test_duckdb_in_memory_connection() -> None:
    """DuckDB can create an in-memory connection."""
    conn = duckdb.connect(":memory:")
    result = conn.execute("SELECT 42 AS answer").fetchone()
    assert result is not None
    assert result[0] == 42
    conn.close()


def test_duckdb_create_table() -> None:
    """DuckDB can create and query a table."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE test (id INTEGER, value VARCHAR)")
    conn.execute("INSERT INTO test VALUES (1, 'hello'), (2, 'world')")
    rows = conn.execute("SELECT * FROM test ORDER BY id").fetchall()
    assert len(rows) == 2
    assert rows[0] == (1, "hello")
    conn.close()
