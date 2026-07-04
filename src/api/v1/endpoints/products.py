"""Product endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.database import get_connection

router = APIRouter()


class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str | None = None
    unit_price: float | None = None


class ProductOut(BaseModel):
    id: str
    sku: str
    name: str
    category: str | None
    unit_price: float | None


@router.get("/", response_model=list[ProductOut])
def list_products() -> list[ProductOut]:
    """List all products."""
    conn = get_connection()
    rows = conn.execute("SELECT id, sku, name, category, unit_price FROM products").fetchall()
    return [ProductOut(id=r[0], sku=r[1], name=r[2], category=r[3], unit_price=r[4]) for r in rows]


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate) -> ProductOut:
    """Create a new product."""
    conn = get_connection()
    pid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO products (id, sku, name, category, unit_price) VALUES (?, ?, ?, ?, ?)",
        [pid, payload.sku, payload.name, payload.category, payload.unit_price],
    )
    return ProductOut(
        id=pid,
        sku=payload.sku,
        name=payload.name,
        category=payload.category,
        unit_price=payload.unit_price,
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str) -> ProductOut:
    """Get a product by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, sku, name, category, unit_price FROM products WHERE id = ?",
        [product_id],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut(id=row[0], sku=row[1], name=row[2], category=row[3], unit_price=row[4])
