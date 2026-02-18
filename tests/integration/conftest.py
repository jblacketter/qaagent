"""Shared fixtures for integration tests — ensures a clean database per test."""

from __future__ import annotations

import pytest

from qaagent import db


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    """Use a fresh temporary database for each test.

    Prevents the auth middleware from blocking requests when the
    developer's real database has users configured.
    """
    db.reset_connection()
    db_file = tmp_path / "test.db"
    db.set_db_path(str(db_file))
    db.get_db()  # initialize
    yield
    db.reset_connection()
