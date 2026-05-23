from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_SCRIPT = REPO_ROOT / ".github" / "scripts" / "validate_deploy.py"


def load_validation_module():
    spec = spec_from_file_location("validate_deploy", VALIDATION_SCRIPT)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validate_repository_layout_flags_missing_assets(tmp_path):
    repo_root = tmp_path
    (repo_root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (repo_root / "backend").mkdir()
    (repo_root / "frontend").mkdir()
    (repo_root / ".env.example").write_text("REDIS_PASSWORD=secret\n", encoding="utf-8")
    (repo_root / "backend" / ".env.example").write_text(
        "OLLAMA_BASE_URL=http://localhost:11434\n",
        encoding="utf-8",
    )
    (repo_root / "frontend" / ".env.example").write_text(
        "VITE_API_URL=http://localhost:8000\n",
        encoding="utf-8",
    )

    validation = load_validation_module()

    errors = validation.validate_repository_layout(repo_root)

    assert any("docker-compose.yml" in error for error in errors)
    assert any("backend/requirements.txt" in error for error in errors)
    assert any("frontend/package.json" in error for error in errors)
    assert any(".github/CODEOWNERS" in error for error in errors)
    assert any(".github/dependabot.yml" in error for error in errors)
    assert any(".github/ISSUE_TEMPLATE/config.yml" in error for error in errors)


def test_validate_repository_layout_flags_missing_env_keys(tmp_path):
    repo_root = tmp_path
    (repo_root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (repo_root / "backend").mkdir()
    (repo_root / "frontend").mkdir()
    (repo_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (repo_root / ".env.example").write_text("", encoding="utf-8")
    (repo_root / "backend" / ".env.example").write_text("", encoding="utf-8")
    (repo_root / "frontend" / ".env.example").write_text("", encoding="utf-8")
    (repo_root / "backend" / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (repo_root / "frontend" / "package.json").write_text("{\"name\":\"frontend\"}\n", encoding="utf-8")
    (repo_root / ".github" / "CODEOWNERS").write_text("* @maintainer\n", encoding="utf-8")
    (repo_root / ".github" / "dependabot.yml").write_text("version: 2\nupdates: []\n", encoding="utf-8")
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text(
        "blank_issues_enabled: false\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").write_text(
        "name: Bug report\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml").write_text(
        "name: Feature request\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "improvement.yml").write_text(
        "name: Improvement\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "question.yml").write_text(
        "name: Question\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text(
        "# Pull Request\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "branch-protection.md").write_text(
        "# Branch Protection\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "workflows").mkdir(parents=True)
    (repo_root / ".github" / "workflows" / "security.yml").write_text(
        "name: Security\n",
        encoding="utf-8",
    )

    validation = load_validation_module()

    errors = validation.validate_repository_layout(repo_root)

    assert any(".env.example" in error and "REDIS_PASSWORD" in error for error in errors)
    assert any("backend/.env.example" in error and "OLLAMA_BASE_URL" in error for error in errors)
    assert any("frontend/.env.example" in error and "VITE_API_URL" in error for error in errors)


def test_validate_repository_layout_passes_for_minimal_valid_repo(tmp_path):
    repo_root = tmp_path
    (repo_root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (repo_root / "backend").mkdir()
    (repo_root / "frontend").mkdir()
    (repo_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (repo_root / ".env.example").write_text("REDIS_PASSWORD=secret\n", encoding="utf-8")
    (repo_root / "backend" / ".env.example").write_text(
        "\n".join(
            [
                "OLLAMA_BASE_URL=http://localhost:11434",
                "QDRANT_URL=http://localhost:6333",
                "DATABASE_URL=sqlite:///./logara.db",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo_root / "frontend" / ".env.example").write_text(
        "VITE_API_URL=http://localhost:8000\nVITE_APP_TITLE=Logara AI\n",
        encoding="utf-8",
    )
    (repo_root / "backend" / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (repo_root / "frontend" / "package.json").write_text("{\"name\":\"frontend\"}\n", encoding="utf-8")
    (repo_root / ".github" / "CODEOWNERS").write_text("* @maintainer\n", encoding="utf-8")
    (repo_root / ".github" / "dependabot.yml").write_text("version: 2\nupdates: []\n", encoding="utf-8")
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "config.yml").write_text(
        "blank_issues_enabled: false\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").write_text(
        "name: Bug report\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml").write_text(
        "name: Feature request\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "improvement.yml").write_text(
        "name: Improvement\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "ISSUE_TEMPLATE" / "question.yml").write_text(
        "name: Question\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text(
        "# Pull Request\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "branch-protection.md").write_text(
        "# Branch Protection\n",
        encoding="utf-8",
    )
    (repo_root / ".github" / "workflows").mkdir(parents=True)
    (repo_root / ".github" / "workflows" / "security.yml").write_text(
        "name: Security\n",
        encoding="utf-8",
    )

    validation = load_validation_module()

    assert validation.validate_repository_layout(repo_root) == []
