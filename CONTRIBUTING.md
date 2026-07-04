# Contributing to Warehouse AI ERP

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/Warehouse-AI-ERP.git`
3. Create a feature branch: `git checkout -b feature/my-feature`
4. Set up development environment (see [DEVELOPMENT.md](DEVELOPMENT.md))

## Development Workflow

1. Make your changes in a feature branch
2. Write or update tests for your changes
3. Ensure all CI checks pass:
   ```bash
   make ci
   ```
4. Commit using clear, descriptive messages
5. Push and open a Pull Request

## Pull Request Guidelines

- Title: Use imperative mood (e.g., "Add warehouse capacity validation")
- Description: Explain **what** and **why**, not how
- Tests: All new features must have tests; bugfixes should include a regression test
- CI: All checks (ruff, black, mypy, pytest) must pass

## Commit Message Format

```
<type>(<scope>): <short summary>

<optional body>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(inventory): add low-stock alert endpoint`
- `fix(db): handle concurrent DuckDB writes correctly`
- `docs(readme): update quick start instructions`

## Code Style

- **Formatter**: `black` (line length 120)
- **Linter**: `ruff`
- **Types**: All public functions must have type annotations
- **Docstrings**: All public modules, classes, and functions must have docstrings

Run `make format` before committing.

## Testing

- Tests live in `tests/`
- Use `pytest` fixtures (see `tests/conftest.py`)
- Each endpoint module should have a corresponding `test_<module>.py`
- Run tests: `make test`
