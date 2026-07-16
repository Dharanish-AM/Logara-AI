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
BACKEND_DIR     := backend
FRONTEND_DIR    := frontend
VENV_DIR        := $(CURDIR)/$(BACKEND_DIR)/.venv

# Detect OS for cross-platform compatibility
ifeq ($(OS),Windows_NT)
  PYTHON_BIN    := $(VENV_DIR)/Scripts/python
  PIP_BIN       := $(VENV_DIR)/Scripts/pip
  ACTIVATE      := $(VENV_DIR)/Scripts/activate
  HAS_RUFF      := $(shell where ruff 2>nul)
  HAS_FLAKE8    := $(shell where flake8 2>nul)
  HAS_NPX       := $(shell where npx 2>nul)
  HAS_UV        := $(shell where uv 2>nul)
  RUFF_VENV     := $(VENV_DIR)/Scripts/ruff.exe
  HAS_RUFF_VENV := $(shell if exist "$(subst /,\,$(RUFF_VENV))" echo yes)
else
  PYTHON_BIN    := $(VENV_DIR)/bin/python
  PIP_BIN       := $(VENV_DIR)/bin/pip
  ACTIVATE      := $(VENV_DIR)/bin/activate
  HAS_RUFF      := $(shell command -v ruff 2>/dev/null)
  HAS_FLAKE8    := $(shell command -v flake8 2>/dev/null)
  HAS_NPX       := $(shell command -v npx 2>/dev/null)
  HAS_UV        := $(shell command -v uv 2>/dev/null)
  RUFF_VENV     := $(VENV_DIR)/bin/ruff
  HAS_RUFF_VENV := $(shell if [ -f "$(RUFF_VENV)" ]; then echo yes; fi)
endif

PYTHON          ?= $(PYTHON_BIN)

# Use uv pip if uv is available, otherwise default to pip bin
ifneq ($(HAS_UV),)
  PIP           := uv pip install
else
  PIP           := "$(PIP_BIN)" install
endif

# Detect ruff inside virtualenv or system PATH
ifneq ($(HAS_RUFF_VENV),)
  RUFF          := "$(RUFF_VENV)"
else ifneq ($(HAS_RUFF),)
  RUFF          := ruff
endif

# ─── Default target ─────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo ""
	@echo "  Logara-AI — Available Make Targets"
	@echo "  ======================================"
	@"$(PYTHON)" -c "import re; [print(f'  \033[36m{m.group(1):<18}\033[0m {m.group(2)}') for line in open('Makefile') for m in [re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)] if m]"
	@echo ""

# ─── Install dependencies ───────────────────────────────────────────────────
install: ## Install Python and Node.js dependencies
	@echo "→ Installing Python dependencies..."
	cd $(BACKEND_DIR) && $(PIP) -r requirements.txt
	@echo "→ Installing Node.js dependencies..."
	cd $(FRONTEND_DIR) && npm install
	@echo "✓ Dependencies installed."

# ─── Service targets ────────────────────────────────────────────────────────
backend: ## Start the FastAPI backend (hot-reload)
	@echo "→ Starting FastAPI backend on http://localhost:8000 ..."
	cd $(BACKEND_DIR) && "$(PYTHON)" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker: ## Start the Redis log processor worker
	@echo "→ Starting log processor worker..."
	cd $(BACKEND_DIR) && "$(PYTHON)" worker.py

frontend: ## Start the React frontend Vite dev server
	@echo "→ Starting frontend on http://localhost:5173 ..."
	cd $(FRONTEND_DIR) && npm run dev

dev: ## Start backend + worker + frontend concurrently in one terminal
	@echo "→ Starting all Logara-AI services..."
	@echo "   Backend  → http://localhost:8000"
	@echo "   Frontend → http://localhost:5173"
	@echo ""
ifneq ($(HAS_NPX),)
	npx concurrently \
		--names "backend,worker,frontend" \
		--prefix-colors "cyan,yellow,magenta" \
		"cd $(BACKEND_DIR) && \"$(PYTHON)\" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000" \
		"cd $(BACKEND_DIR) && \"$(PYTHON)\" worker.py" \
		"cd $(FRONTEND_DIR) && npm run dev"
else
	@echo "npx not found. Run 'npm install -g concurrently' or start each service manually."
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make worker"
	@echo "  Terminal 3: make frontend"
	@exit 1
endif

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
	cd $(BACKEND_DIR) && "$(PYTHON)" -m pytest \
	  --cov=. \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov \
	  -v
	@echo "✓ Tests complete. Coverage HTML report: backend/htmlcov/index.html"

test-fast: ## Run tests without coverage (faster feedback loop)
	cd $(BACKEND_DIR) && "$(PYTHON)" -m pytest -q --tb=short

lint: ## Run Python linting on the backend
	@echo "→ Linting backend Python code..."
ifneq ($(RUFF),)
	cd $(BACKEND_DIR) && $(RUFF) check .
else
ifneq ($(HAS_FLAKE8),)
	cd $(BACKEND_DIR) && flake8 . --max-line-length=120 --exclude=.venv,__pycache__
else
	@echo "No linter found. Install ruff: pip install ruff"
endif
endif

# ─── Cleanup ────────────────────────────────────────────────────────────────
clean: ## Remove Python bytecode, test artifacts and coverage reports
	@echo "→ Cleaning build artifacts..."
ifeq ($(OS),Windows_NT)
	-rd /s /q "$(BACKEND_DIR)\__pycache__" 2>nul
	-rd /s /q "$(BACKEND_DIR)\.pytest_cache" 2>nul
	-rd /s /q "$(BACKEND_DIR)\htmlcov" 2>nul
	-del /q /f "$(BACKEND_DIR)\coverage.xml" 2>nul
	-del /s /q /f *.pyc 2>nul
else
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
endif
	@echo "✓ Clean complete."
