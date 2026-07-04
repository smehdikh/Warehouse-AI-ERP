# Warehouse AI ERP

> An intelligent Warehouse & ERP system powered by **FastAPI**, **DuckDB**, and AI.

[![CI](https://github.com/smehdikh/Warehouse-AI-ERP/actions/workflows/ci.yml/badge.svg)](https://github.com/smehdikh/Warehouse-AI-ERP/actions/workflows/ci.yml)

## Features

- 📦 Warehouse management (locations, capacity)
- 🏷️ Product catalog (SKU, categories, pricing)
- 📊 Inventory tracking powered by DuckDB OLAP
- 🚀 FastAPI with auto-generated OpenAPI docs
- 🐳 Docker-ready for development and production

## Quick Start

```bash
# Clone and setup
git clone https://github.com/smehdikh/Warehouse-AI-ERP.git
cd Warehouse-AI-ERP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy env file
cp .env.example .env

# Start the server
uvicorn src.main:app --reload
```

Open <http://localhost:8000/docs> for interactive API documentation.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for the full development guide.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI |
| Database | DuckDB |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Testing | pytest |
| Linting | ruff, black, mypy |

## License

MIT
