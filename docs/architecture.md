# Architecture

## Overview

Warehouse AI ERP is a FastAPI-based backend service using DuckDB as the analytical database engine.

## Components

- **FastAPI**: High-performance async web framework
- **DuckDB**: Embedded OLAP database for analytical queries
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server

## Directory Structure

```
src/
├── api/v1/endpoints/   # REST API endpoints
├── core/               # Configuration, security
├── db/                 # Database connection and schema
└── main.py             # Application entry point

tests/                  # pytest test suite
docs/                   # Documentation
scripts/                # Utility scripts
docker/                 # Docker configuration
.github/workflows/      # CI/CD pipelines
```
