.PHONY: test lint typecheck clean install check test-integration

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

lint:
	ruff check src tests
	ruff format --check src tests

typecheck:
	mypy --strict src

check: lint typecheck test

test-integration:
	pytest tests/integration -v -m integration

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
