.PHONY: help install dev lint format typecheck test clean run docker-build docker-up

PYTHON := python3
VENV := venv
BIN := $(VENV)/bin

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies in a virtual environment
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e ".[dev]"

dev: ## Run development server with hot reload
	$(BIN)/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

lint: ## Run ruff linter
	$(BIN)/ruff check src tests

format: ## Auto-format code with black and ruff
	$(BIN)/black src tests
	$(BIN)/ruff check --fix src tests

format-check: ## Check formatting without modifying files
	$(BIN)/black --check src tests

typecheck: ## Run mypy type checker
	$(BIN)/mypy src

test: ## Run pytest test suite
	$(BIN)/pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	$(BIN)/pytest tests/ -v --cov=src --cov-report=html

ci: lint format-check typecheck test ## Run all CI checks

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ | xargs rm -rf
	find . -name "*.pyc" -delete
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov
	rm -f warehouse.db

seed: ## Seed database with sample data
	$(BIN)/python scripts/seed_db.py

docker-build: ## Build Docker image
	docker build -t warehouse-ai-erp .

docker-up: ## Start services with docker-compose
	docker-compose up --build
