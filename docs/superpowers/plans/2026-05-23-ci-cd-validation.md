# CI/CD Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GitHub Actions workflows and deploy-validation checks that verify backend, frontend, and infrastructure readiness for Logara AI.

**Architecture:** Use a reusable GitHub Actions workflow as the shared execution layer for CI and pre-deploy automation. Keep deploy-specific repository checks in a dedicated Python script so they can be tested and reviewed like application code.

**Tech Stack:** GitHub Actions, Python, pytest, Node.js, npm, Docker Compose

---

### Task 1: Add the failing validation tests

**Files:**
- Create: `backend/tests/test_deploy_validation.py`

- [ ] **Step 1: Write the failing test**

```python
def test_validate_repository_layout_passes_for_minimal_valid_repo(tmp_path):
    validation = load_validation_module()
    assert validation.validate_repository_layout(tmp_path) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_deploy_validation.py -q`
Expected: `FAIL` because `.github/scripts/validate_deploy.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def validate_repository_layout(repo_root: Path) -> list[str]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_deploy_validation.py -q`
Expected: Test passes with the stub. Additional tests in later tasks will drive full implementation.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_deploy_validation.py .github/scripts/validate_deploy.py
git commit -m "test: cover deploy validation script"
```

### Task 2: Add reusable GitHub Actions workflows

**Files:**
- Create: `.github/workflows/repo-validation.yml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/pre-deploy.yml`

- [ ] **Step 1: Write the failing test**

```python
def test_validate_repository_layout_flags_missing_assets(tmp_path):
    validation = load_validation_module()
    errors = validation.validate_repository_layout(tmp_path)
    assert any("docker-compose.yml" in error for error in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_deploy_validation.py -q`
Expected: `FAIL` until the repository validation logic exists.

- [ ] **Step 3: Write minimal implementation**

```yaml
jobs:
  backend:
    runs-on: ubuntu-latest
  frontend:
    runs-on: ubuntu-latest
  infrastructure:
    runs-on: ubuntu-latest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose config`
Expected: Compose file renders without syntax errors.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/repo-validation.yml .github/workflows/ci.yml .github/workflows/pre-deploy.yml
git commit -m "feat: add repository validation workflows"
```

### Task 3: Tighten frontend lint scope and document the pipeline

**Files:**
- Modify: `frontend/eslint.config.js`
- Modify: `README.md`
- Create: `docs/superpowers/specs/2026-05-23-ci-cd-design.md`
- Create: `docs/superpowers/plans/2026-05-23-ci-cd-validation.md`

- [ ] **Step 1: Write the failing test**

```python
def test_validate_repository_layout_flags_missing_env_keys(tmp_path):
    validation = load_validation_module()
    errors = validation.validate_repository_layout(tmp_path)
    assert any("REDIS_PASSWORD" in error for error in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_deploy_validation.py -q`
Expected: `FAIL` until required env-key validation is implemented.

- [ ] **Step 3: Write minimal implementation**

```javascript
export default defineConfig([
  globalIgnores(['dist', 'node_modules']),
])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run lint`
Expected: ESLint completes against source files without spending time under `node_modules`.

- [ ] **Step 5: Commit**

```bash
git add frontend/eslint.config.js README.md docs/superpowers/specs/2026-05-23-ci-cd-design.md docs/superpowers/plans/2026-05-23-ci-cd-validation.md
git commit -m "docs: describe ci and deploy validation"
```
