"""Warehouse AI ERP - FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings
from src.db.database import init_db


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown."""
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Warehouse AI ERP System powered by FastAPI and DuckDB",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}
