"""DuckDB database configuration and connection management."""

import duckdb

from src.core.config import settings

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return the global DuckDB connection (thread-safe read via cursor)."""
    global _connection
    if _connection is None:
        _connection = duckdb.connect(
            database=settings.DUCKDB_DATABASE,
            read_only=settings.DUCKDB_READ_ONLY,
        )
    return _connection


def init_db() -> None:
    """Initialize the database schema."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            id          VARCHAR PRIMARY KEY,
            name        VARCHAR NOT NULL,
            location    VARCHAR,
            capacity    DOUBLE,
            created_at  TIMESTAMP DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          VARCHAR PRIMARY KEY,
            sku         VARCHAR NOT NULL UNIQUE,
            name        VARCHAR NOT NULL,
            category    VARCHAR,
            unit_price  DOUBLE,
            created_at  TIMESTAMP DEFAULT now()
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id           VARCHAR PRIMARY KEY,
            warehouse_id VARCHAR NOT NULL,
            product_id   VARCHAR NOT NULL,
            quantity     INTEGER DEFAULT 0,
            updated_at   TIMESTAMP DEFAULT now()
        )
    """)


def close_connection() -> None:
    """Close the DuckDB connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
