# Development Guide

## Prerequisites

- Python 3.12+
- Git
- Docker (optional, for containerised development)

## Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/smehdikh/Warehouse-AI-ERP.git
cd Warehouse-AI-ERP

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Install all dependencies (including dev tools)
pip install -e ".[dev]"

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env as needed

# 5. Start the dev server
uvicorn src.main:app --reload
```

Visit <http://localhost:8000/docs> to explore the API.

## Project Structure

```
src/
├── api/
│   └── v1/
│       ├── endpoints/
│       │   ├── warehouses.py
│       │   ├── products.py
│       │   └── inventory.py
│       └── router.py
├── core/
│   └── config.py          # Settings (pydantic-settings)
├── db/
│   └── database.py        # DuckDB connection & schema
└── main.py                # FastAPI app factory

tests/
├── conftest.py            # Fixtures (in-memory DuckDB)
├── test_health.py
├── test_warehouses.py
├── test_products.py
└── test_duckdb.py

scripts/
└── seed_db.py             # Sample data seeder

docker/
└── Dockerfile.dev         # Dev-mode Docker image

.github/
└── workflows/
    └── ci.yml             # GitHub Actions CI pipeline
```

## Quality Tools

| Tool | Purpose | Command |
|------|---------|---------|
| ruff | Linting | `make lint` |
| black | Formatting | `make format` |
| mypy | Type checking | `make typecheck` |
| pytest | Testing | `make test` |

Run all checks at once: `make ci`

## DuckDB Notes

- DuckDB is embedded — no external server needed
- Database file: `warehouse.db` (configurable via `DUCKDB_DATABASE` env var)
- For tests, an in-memory database is used automatically (see `conftest.py`)
- DuckDB supports concurrent reads but serialises writes

## Environment Variables

All variables are documented in `.env.example`. The most important ones:

| Variable | Default | Description |
|----------|---------|-------------|
| `DUCKDB_DATABASE` | `warehouse.db` | Path to DuckDB file |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `SECRET_KEY` | `changeme-...` | JWT signing key — **change in prod** |
| `DEBUG` | `true` | Enable debug mode |

## Docker Development

```bash
# Build and start
docker-compose up --build

# Stop
docker-compose down
```

## Adding a New Endpoint Module

1. Create `src/api/v1/endpoints/<module>.py`
2. Define a `router = APIRouter()` and add routes
3. Include it in `src/api/v1/router.py`
4. Add `tests/test_<module>.py`
5. Run `make ci` to verify
