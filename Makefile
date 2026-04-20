.PHONY: test lint typecheck clean install check

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

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
