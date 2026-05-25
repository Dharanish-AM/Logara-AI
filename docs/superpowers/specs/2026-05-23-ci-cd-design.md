# CI/CD Validation Design

## Goal

Add maintainable GitHub Actions workflows that verify backend quality, frontend quality, infrastructure configuration, and deploy-readiness using checks that can also be reasoned about locally.

## Recommended Approach

Use a reusable workflow in `.github/workflows/repo-validation.yml` as the single source of truth for repository validation. Trigger it from a pull-request-focused CI workflow and a main-branch pre-deploy workflow.

## Design Summary

- Backend validation installs `backend/requirements.txt`, compiles imports with `python -m compileall .`, and runs `pytest`.
- Frontend validation installs from `package-lock.json`, runs ESLint, and performs a production Vite build.
- Infrastructure validation runs a repository-level Python script that checks required repo assets and expected `.env.example` keys, then validates `docker compose config`.
- Deploy readiness extends the baseline checks with smoke imports for the FastAPI app and worker so the main branch stays in a deployable state.

## Auditability

- Shared validation logic is centralized instead of duplicated across multiple workflows.
- Deploy prerequisites are expressed in a versioned script under `.github/scripts/validate_deploy.py`.
- The deployment validation script is covered by pytest tests in `backend/tests/test_deploy_validation.py`.
