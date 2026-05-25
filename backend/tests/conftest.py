"""
Pytest configuration for backend tests.
Ensures backend modules are importable during test execution.
"""

import sys
from pathlib import Path

# Resolve the backend root so tests are runnable from any working directory
# (project root, backend/, or tests/) without ModuleNotFoundError.
ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))