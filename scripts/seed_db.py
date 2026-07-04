#!/usr/bin/env python3
"""Seed the database with sample data."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.database import init_db, get_connection
import uuid


def seed() -> None:
    """Insert sample warehouses, products, and inventory."""
    init_db()
    conn = get_connection()

    wid = str(uuid.uuid4())
    conn.execute(
        "INSERT OR IGNORE INTO warehouses (id, name, location, capacity) VALUES (?, ?, ?, ?)",
        [wid, "Main Warehouse", "New York", 10000.0],
    )

    pid = str(uuid.uuid4())
    conn.execute(
        "INSERT OR IGNORE INTO products (id, sku, name, category, unit_price) VALUES (?, ?, ?, ?, ?)",
        [pid, "SKU-001", "Widget A", "Electronics", 9.99],
    )

    conn.execute(
        "INSERT INTO inventory (id, warehouse_id, product_id, quantity) VALUES (?, ?, ?, ?)",
        [str(uuid.uuid4()), wid, pid, 500],
    )

    print("✓ Database seeded successfully")


if __name__ == "__main__":
    seed()
