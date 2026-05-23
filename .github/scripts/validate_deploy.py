from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_PATHS = (
    "docker-compose.yml",
    "backend/requirements.txt",
    "frontend/package.json",
    "backend/.env.example",
    "frontend/.env.example",
    ".env.example",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/branch-protection.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/improvement.yml",
    ".github/ISSUE_TEMPLATE/question.yml",
    ".github/workflows/security.yml",
)

REQUIRED_ENV_KEYS = {
    ".env.example": ("REDIS_PASSWORD",),
    "backend/.env.example": (
        "OLLAMA_BASE_URL",
        "QDRANT_URL",
        "DATABASE_URL",
    ),
    "frontend/.env.example": (
        "VITE_API_URL",
        "VITE_APP_TITLE",
    ),
}


def parse_env_keys(env_path: Path) -> set[str]:
    keys: set[str] = set()

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key:
            keys.add(key)

    return keys


def validate_repository_layout(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for relative_path in REQUIRED_PATHS:
        if not (repo_root / relative_path).exists():
            errors.append(f"Missing required repository asset: {relative_path}")

    for relative_path, required_keys in REQUIRED_ENV_KEYS.items():
        env_path = repo_root / relative_path
        if not env_path.exists():
            continue

        env_keys = parse_env_keys(env_path)
        missing_keys = [key for key in required_keys if key not in env_keys]
        if missing_keys:
            missing_keys_display = ", ".join(missing_keys)
            errors.append(
                f"Missing required keys in {relative_path}: {missing_keys_display}"
            )

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors = validate_repository_layout(repo_root)

    if errors:
        print("Deployment validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Deployment validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
