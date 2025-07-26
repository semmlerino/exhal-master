# SpritePal Development Automation
# Usage: make <target>

.PHONY: help install install-dev clean test test-unit test-gui lint format type-check security \
        pre-commit build run coverage docs docker-build docker-run setup all-checks ci

# Default target
help: ## Show this help message
	@echo "SpritePal Development Commands"
	@echo "=============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment Setup
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r dev-requirements.txt
	pre-commit install

setup: install-dev ## Complete development environment setup
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything works"

# Cleaning
clean: ## Clean generated files and caches
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -f .coverage
	rm -f coverage.xml

# Testing
test: ## Run all tests with coverage
	pytest spritepal/tests/ -v --cov=spritepal --cov-report=html --cov-report=term -m "not gui"

test-unit: ## Run unit tests only (fast)
	pytest spritepal/tests/ -v -m "unit" --tb=short

test-gui: ## Run GUI tests (requires display)
	pytest spritepal/tests/ -v -m "gui" --tb=short

test-integration: ## Run integration tests
	pytest spritepal/tests/ -v -m "integration" --tb=short

test-all: ## Run all tests including GUI tests
	pytest spritepal/tests/ -v --cov=spritepal --cov-report=html --tb=short

# Code Quality
lint: ## Run linting checks
	ruff check spritepal/

lint-fix: ## Fix linting issues automatically
	ruff check spritepal/ --fix

format: ## Format code
	ruff format spritepal/

format-check: ## Check code formatting
	ruff format spritepal/ --check

type-check: ## Run type checking
	mypy spritepal/

security: ## Run security scans
	bandit -r spritepal/ -f screen
	safety check

# Pre-commit
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# All Quality Checks
all-checks: lint type-check security test-unit ## Run all quality checks

ci: clean all-checks test ## Run full CI pipeline

# Application
run: ## Launch SpritePal application
	cd spritepal && python launch_spritepal.py

run-debug: ## Launch SpritePal with debug logging
	cd spritepal && PYTHONPATH=.. python launch_spritepal.py --debug

# Building
build: clean ## Build distribution packages
	python -m build

build-check: build ## Build and check distribution
	twine check dist/*

# Documentation
docs: ## Generate documentation
	sphinx-build -b html docs/ docs/_build/html

docs-serve: docs ## Serve documentation locally
	python -m http.server 8000 -d docs/_build/html

# Coverage
coverage: ## Generate coverage report
	pytest spritepal/tests/ --cov=spritepal --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

coverage-open: coverage ## Open coverage report in browser
	python -m webbrowser htmlcov/index.html

# Docker (for future use)
docker-build: ## Build Docker development image
	docker build -t spritepal-dev .

docker-run: ## Run SpritePal in Docker container
	docker run -it --rm \
		-v $(PWD):/workspace \
		-e DISPLAY=$(DISPLAY) \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		spritepal-dev

# Development Utilities
profile: ## Run application with profiling
	python -m cProfile -o profile_output.prof spritepal/launch_spritepal.py
	python -c "import pstats; pstats.Stats('profile_output.prof').sort_stats('cumulative').print_stats(20)"

deps-update: ## Update dependencies
	pip-compile --upgrade requirements.in
	pip-compile --upgrade dev-requirements.in

deps-install: ## Install exact dependency versions
	pip install -r requirements.txt -r dev-requirements.txt

# Verification
verify-setup: ## Verify development environment setup
	@echo "Verifying Python environment..."
	python --version
	@echo "Verifying dependencies..."
	python -c "import PyQt6; print('PyQt6:', PyQt6.QtCore.PYQT_VERSION_STR)"
	python -c "import PIL; print('Pillow:', PIL.__version__)"
	python -c "import numpy; print('NumPy:', numpy.__version__)"
	@echo "Verifying tools..."
	ruff --version
	mypy --version
	pytest --version
	@echo "Environment verification complete!"

# Quick development cycle
quick: format lint-fix test-unit ## Quick development cycle: format, fix lint, run unit tests

# Full development cycle  
full: clean format lint type-check security test coverage ## Full development cycle with all checks

# Help is default
.DEFAULT_GOAL := help