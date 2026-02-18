"""Shared fixtures for API tests — ensures a clean database per test."""

from __future__ import annotations

import pytest

from qaagent import db


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    """Use a fresh temporary database for each test.

    This ensures db.user_count() == 0 (setup mode) for tests that don't
    create users, and prevents cross-test contamination.
    """
    db.reset_connection()
    db_file = tmp_path / "test.db"
    db.set_db_path(str(db_file))
    db.get_db()  # initialize
    yield
    db.reset_connection()
