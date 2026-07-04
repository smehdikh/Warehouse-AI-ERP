"""Warehouse endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.database import get_connection

router = APIRouter()


class WarehouseCreate(BaseModel):
    name: str
    location: str | None = None
    capacity: float | None = None


class WarehouseOut(BaseModel):
    id: str
    name: str
    location: str | None
    capacity: float | None


@router.get("/", response_model=list[WarehouseOut])
def list_warehouses() -> list[WarehouseOut]:
    """List all warehouses."""
    conn = get_connection()
    rows = conn.execute("SELECT id, name, location, capacity FROM warehouses").fetchall()
    return [WarehouseOut(id=r[0], name=r[1], location=r[2], capacity=r[3]) for r in rows]


@router.post("/", response_model=WarehouseOut, status_code=201)
def create_warehouse(payload: WarehouseCreate) -> WarehouseOut:
    """Create a new warehouse."""
    conn = get_connection()
    wid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO warehouses (id, name, location, capacity) VALUES (?, ?, ?, ?)",
        [wid, payload.name, payload.location, payload.capacity],
    )
    return WarehouseOut(
        id=wid,
        name=payload.name,
        location=payload.location,
        capacity=payload.capacity,
    )


@router.get("/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: str) -> WarehouseOut:
    """Get a warehouse by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, location, capacity FROM warehouses WHERE id = ?",
        [warehouse_id],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseOut(id=row[0], name=row[1], location=row[2], capacity=row[3])
