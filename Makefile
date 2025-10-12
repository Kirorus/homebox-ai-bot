SHELL := /bin/bash
PROJECT_DIR := $(CURDIR)

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help venv env run stop restart test coverage i18n-check docker-build docker-deploy compose-up compose-down clean format lint check

help: ## Show available make targets
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' | sort

venv: ## Create virtual environment and install dependencies
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) -q install --upgrade pip
	@test -f requirements.txt && $(PIP) -q install -r requirements.txt || true

env: ## Create .env from env.example if not exists
	@test -f .env || (test -f env.example && cp env.example .env && echo ".env created" || echo "env.example not found; skipped")

run: venv ## Start the bot locally
	@echo "🤖 Starting HomeBox AI Bot..."
	@cd src && $(PYTHON) main.py

stop: ## Stop running bot processes
	@echo "🛑 Stopping HomeBox AI Bot..."
	@pkill -f "python.*main.py" || echo "No bot processes found"

restart: ## Restart bot
	@$(MAKE) stop && sleep 2 && $(MAKE) run

test: venv ## Run tests
	@./run_tests.sh

coverage: venv ## Run tests with coverage (if supported by run_tests.sh)
	@COVERAGE=1 ./run_tests.sh

i18n-check: venv ## Validate i18n keys/files
	@$(PYTHON) scripts/check_i18n.py

docker-build: ## Build docker image
	@echo "🐳 Building Docker image..."
	@docker build -t homebox-ai-bot:latest .

docker-deploy: ## Deploy using docker-compose
	@echo "🚀 Deploying with docker-compose..."
	@$(MAKE) compose-up

compose-up: ## Start services via docker compose
	@if docker compose version >/dev/null 2>&1; then docker compose up -d; else docker-compose up -d; fi

compose-down: ## Stop services via docker compose
	@if docker compose version >/dev/null 2>&1; then docker compose down; else docker-compose down; fi

clean: ## Remove caches and build artifacts
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache build dist *.egg-info 2>/dev/null || true

format: venv ## Auto-format using black/isort if available in venv
	@test -x $(VENV)/bin/black && $(VENV)/bin/black . || echo "black not installed; skipped"
	@test -x $(VENV)/bin/isort && $(VENV)/bin/isort . || echo "isort not installed; skipped"

lint: venv ## Lint using ruff or flake8 if available in venv
	@if test -x $(VENV)/bin/ruff; then $(VENV)/bin/ruff check .; \
	elif test -x $(VENV)/bin/flake8; then $(VENV)/bin/flake8 .; \
	else echo "No linter (ruff/flake8) installed"; fi

check: test i18n-check ## Run test suite and i18n checks