"""
conftest.py — Isolates the test environment from the real development database.

This file MUST be the first module-level code executed by pytest before any
app module is imported. pytest guarantees conftest.py in the tests/ directory
is loaded before collecting test files in the same directory.

However, because test_api.py imports `from app.main import app` at module level,
and `settings = Settings()` is a module-level singleton in config.py, we must
set the DATABASE_URL env var before pytest begins collecting.

We do this by using a pytest plugin hook (pytest_configure) which runs before
any test module is imported.
"""
import os
import pathlib

TEST_DB_PATH = pathlib.Path(__file__).parent / "test_paventra.db"


def pytest_configure(config):
    """Called by pytest before any test collection. Override DATABASE_URL here."""
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    os.environ["MODEL_ENABLED"] = "false"  # Disable YOLO in tests for speed
    os.environ["ENVIRONMENT"] = "test"
