# =============================================================================
# Logara-AI — Developer Makefile
# =============================================================================
# Usage:
#   make dev          — Start all services concurrently (backend + worker + frontend)
#   make backend      — Start only the FastAPI backend
#   make worker       — Start only the Redis log worker
#   make frontend     — Start only the React frontend (Vite dev server)
#   make test         — Run the full backend test suite with coverage
#   make lint         — Run Python linting (ruff or flake8)
#   make docker-up    — Start all Docker services (Redis + Qdrant + Ollama)
#   make docker-down  — Stop all Docker services
#   make install      — Install all Python + Node dependencies
#   make clean        — Remove Python bytecode and test artifacts
# =============================================================================

.PHONY: dev backend worker frontend test lint docker-up docker-down install clean help

# ─── Configuration ──────────────────────────────────────────────────────────
PYTHON          ?= python
PIP             ?= pip
VENV_DIR        := backend/.venv
BACKEND_DIR     := backend
FRONTEND_DIR    := frontend

# Detect OS for cross-platform compatibility
ifeq ($(OS),Windows_NT)
  PYTHON_BIN    := $(VENV_DIR)/Scripts/python
  PIP_BIN       := $(VENV_DIR)/Scripts/pip
  ACTIVATE      := $(VENV_DIR)/Scripts/activate
else
  PYTHON_BIN    := $(VENV_DIR)/bin/python
  PIP_BIN       := $(VENV_DIR)/bin/pip
  ACTIVATE      := $(VENV_DIR)/bin/activate
endif

# ─── Default target ─────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo ""
	@echo "  Logara-AI — Available Make Targets"
	@echo "  ======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ─── Install dependencies ───────────────────────────────────────────────────
install: ## Install Python and Node.js dependencies
	@echo "→ Installing Python dependencies..."
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt
	@echo "→ Installing Node.js dependencies..."
	cd $(FRONTEND_DIR) && npm install
	@echo "✓ Dependencies installed."

# ─── Service targets ────────────────────────────────────────────────────────
backend: ## Start the FastAPI backend (hot-reload)
	@echo "→ Starting FastAPI backend on http://localhost:8000 ..."
	cd $(BACKEND_DIR) && uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker: ## Start the Redis log processor worker
	@echo "→ Starting log processor worker..."
	cd $(BACKEND_DIR) && $(PYTHON) worker.py

frontend: ## Start the React frontend Vite dev server
	@echo "→ Starting frontend on http://localhost:5173 ..."
	cd $(FRONTEND_DIR) && npm run dev

dev: ## Start backend + worker + frontend concurrently in one terminal
	@echo "→ Starting all Logara-AI services..."
	@echo "   Backend  → http://localhost:8000"
	@echo "   Frontend → http://localhost:5173"
	@echo ""
	@if command -v npx >/dev/null 2>&1; then \
	  npx concurrently \
	    --names "backend,worker,frontend" \
	    --prefix-colors "cyan,yellow,magenta" \
	    "cd $(BACKEND_DIR) && uvicorn main:app --reload --host 0.0.0.0 --port 8000" \
	    "cd $(BACKEND_DIR) && $(PYTHON) worker.py" \
	    "cd $(FRONTEND_DIR) && npm run dev"; \
	else \
	  echo "npx not found. Run 'npm install -g concurrently' or start each service manually."; \
	  echo "  Terminal 1: make backend"; \
	  echo "  Terminal 2: make worker"; \
	  echo "  Terminal 3: make frontend"; \
	  exit 1; \
	fi

# ─── Docker targets ─────────────────────────────────────────────────────────
docker-up: ## Start infrastructure services (Redis, Qdrant, Ollama) via Docker Compose
	@echo "→ Starting Docker services..."
	docker compose up -d redis qdrant ollama
	@echo "✓ Services started. Redis: 6379 | Qdrant: 6333 | Ollama: 11434"

docker-down: ## Stop all Docker Compose services
	@echo "→ Stopping Docker services..."
	docker compose down
	@echo "✓ Services stopped."

docker-full: ## Start ALL services including backend and frontend in Docker
	docker compose up --build

# ─── Test & quality targets ─────────────────────────────────────────────────
test: ## Run the full backend test suite with coverage report
	@echo "→ Running backend tests with coverage..."
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest \
	  --cov=. \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov \
	  -v
	@echo "✓ Tests complete. Coverage HTML report: backend/htmlcov/index.html"

test-fast: ## Run tests without coverage (faster feedback loop)
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q --tb=short

lint: ## Run Python linting on the backend
	@echo "→ Linting backend Python code..."
	@if command -v ruff >/dev/null 2>&1; then \
	  cd $(BACKEND_DIR) && ruff check .; \
	elif command -v flake8 >/dev/null 2>&1; then \
	  cd $(BACKEND_DIR) && flake8 . --max-line-length=120 --exclude=.venv,__pycache__; \
	else \
	  echo "No linter found. Install ruff: pip install ruff"; \
	fi

# ─── Cleanup ────────────────────────────────────────────────────────────────
clean: ## Remove Python bytecode, test artifacts and coverage reports
	@echo "→ Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	@echo "✓ Clean complete."
