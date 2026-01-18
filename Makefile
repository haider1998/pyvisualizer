.PHONY: install install-dev test lint format type-check clean docs help

# Default target
help:
	@echo "PyVisualizer Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install package in editable mode"
	@echo "  make install-dev   - Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linters (flake8, mypy)"
	@echo "  make format        - Format code with black and isort"
	@echo "  make type-check    - Run type checking with mypy"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          - Generate architecture diagrams"
	@echo "  make self-viz      - Visualize PyVisualizer itself"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Remove build artifacts"
	@echo "  make build         - Build distribution packages"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=pyvisualizer --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

# Code quality
lint:
	@echo "Running flake8..."
	flake8 pyvisualizer tests --max-line-length=100 --ignore=E501,W503
	@echo "Running mypy..."
	mypy pyvisualizer --ignore-missing-imports

format:
	@echo "Running black..."
	black pyvisualizer tests
	@echo "Running isort..."
	isort pyvisualizer tests

type-check:
	mypy pyvisualizer --ignore-missing-imports

# Documentation
docs:
	mkdir -p docs/architecture
	py-code-visualizer pyvisualizer --format mermaid --output docs/architecture/architecture.mmd --max-nodes 100 --exclude tests
	py-code-visualizer pyvisualizer --format html --output docs/architecture/interactive.html --max-nodes 100 --exclude tests
	@echo "Diagrams generated in docs/architecture/"

self-viz:
	py-code-visualizer pyvisualizer --format html --output pyvisualizer_architecture.html --max-nodes 100
	@echo "Visualization saved to pyvisualizer_architecture.html"

# Clean
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build
build: clean
	pip install build
	python -m build

# Release (test PyPI)
release-test: build
	pip install twine
	twine upload --repository testpypi dist/*

# Release (production PyPI)
release: build
	pip install twine
	twine upload dist/*
