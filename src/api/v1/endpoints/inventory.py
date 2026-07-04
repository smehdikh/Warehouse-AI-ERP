"""Inventory endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.database import get_connection

router = APIRouter()


class InventoryCreate(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: int = 0


class InventoryOut(BaseModel):
    id: str
    warehouse_id: str
    product_id: str
    quantity: int


@router.get("/", response_model=list[InventoryOut])
def list_inventory() -> list[InventoryOut]:
    """List all inventory records."""
    conn = get_connection()
    rows = conn.execute("SELECT id, warehouse_id, product_id, quantity FROM inventory").fetchall()
    return [InventoryOut(id=r[0], warehouse_id=r[1], product_id=r[2], quantity=r[3]) for r in rows]


@router.post("/", response_model=InventoryOut, status_code=201)
def create_inventory(payload: InventoryCreate) -> InventoryOut:
    """Create an inventory record."""
    conn = get_connection()
    iid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO inventory (id, warehouse_id, product_id, quantity) VALUES (?, ?, ?, ?)",
        [iid, payload.warehouse_id, payload.product_id, payload.quantity],
    )
    return InventoryOut(
        id=iid,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
    )


@router.get("/{inventory_id}", response_model=InventoryOut)
def get_inventory(inventory_id: str) -> InventoryOut:
    """Get an inventory record by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, warehouse_id, product_id, quantity FROM inventory WHERE id = ?",
        [inventory_id],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    return InventoryOut(id=row[0], warehouse_id=row[1], product_id=row[2], quantity=row[3])
