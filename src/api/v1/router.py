"""API v1 router aggregating all endpoint modules."""

from fastapi import APIRouter

from src.api.v1.endpoints import inventory, products, warehouses

api_router = APIRouter()

api_router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
