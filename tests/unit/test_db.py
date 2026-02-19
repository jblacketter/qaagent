"""Unit tests for qaagent.db — SQLite persistence layer."""
from __future__ import annotations

import pytest

from qaagent import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Each test gets its own fresh SQLite database."""
    db.reset_connection()
    db.set_db_path(str(tmp_path / "test.db"))
    yield
    db.reset_connection()


# ---------------------------------------------------------------------------
# Repository CRUD
# ---------------------------------------------------------------------------

class TestRepoCRUD:
    def test_upsert_and_get(self):
        db.repo_upsert("r1", "Repo One", "/tmp/r1", "local", analysis_options={"security": True})
        row = db.repo_get("r1")
        assert row is not None
        assert row["name"] == "Repo One"
        assert row["path"] == "/tmp/r1"
        assert row["repo_type"] == "local"
        assert row["analysis_options"] == {"security": True}
        assert row["status"] == "ready"
        assert row["run_count"] == 0

    def test_get_missing(self):
        assert db.repo_get("nonexistent") is None

    def test_upsert_updates(self):
        db.repo_upsert("r1", "Old", "/old")
        db.repo_upsert("r1", "New", "/new", status="analyzing")
        row = db.repo_get("r1")
        assert row["name"] == "New"
        assert row["path"] == "/new"
        assert row["status"] == "analyzing"

    def test_list(self):
        db.repo_upsert("b", "Beta", "/b")
        db.repo_upsert("a", "Alpha", "/a")
        repos = db.repo_list()
        assert len(repos) == 2
        # Ordered by name
        assert repos[0]["name"] == "Alpha"
        assert repos[1]["name"] == "Beta"

    def test_delete(self):
        db.repo_upsert("r1", "R1", "/r1")
        assert db.repo_delete("r1") is True
        assert db.repo_get("r1") is None

    def test_delete_missing(self):
        assert db.repo_delete("nope") is False

    def test_delete_cascades_branch_data(self):
        """Deleting a repo must remove all associated branch data."""
        db.repo_upsert("r1", "R1", "/r1")
        conn = db.get_db()
        # Create a branch, checklist, checklist item, and test run
        conn.execute(
            "INSERT INTO branches (repo_id, branch_name, stage) VALUES ('r1', 'feature/X', 'active')"
        )
        branch_id = conn.execute("SELECT id FROM branches WHERE repo_id = 'r1'").fetchone()["id"]
        conn.execute(
            "INSERT INTO branch_checklists (branch_id, format) VALUES (?, 'checklist')",
            (branch_id,),
        )
        cl_id = conn.execute("SELECT id FROM branch_checklists WHERE branch_id = ?", (branch_id,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO branch_checklist_items (checklist_id, description) VALUES (?, 'test item')",
            (cl_id,),
        )
        conn.execute(
            "INSERT INTO branch_test_runs (branch_id, suite_type, total, passed) VALUES (?, 'pytest', 5, 5)",
            (branch_id,),
        )
        conn.commit()

        # Delete repo — must not raise, must cascade
        assert db.repo_delete("r1") is True
        assert conn.execute("SELECT COUNT(*) as c FROM branches").fetchone()["c"] == 0
        assert conn.execute("SELECT COUNT(*) as c FROM branch_checklists").fetchone()["c"] == 0
        assert conn.execute("SELECT COUNT(*) as c FROM branch_checklist_items").fetchone()["c"] == 0
        assert conn.execute("SELECT COUNT(*) as c FROM branch_test_runs").fetchone()["c"] == 0

    def test_update_status(self):
        db.repo_upsert("r1", "R1", "/r1")
        db.repo_update_status("r1", "error", last_scan="2025-01-01", run_count=3)
        row = db.repo_get("r1")
        assert row["status"] == "error"
        assert row["last_scan"] == "2025-01-01"
        assert row["run_count"] == 3


# ---------------------------------------------------------------------------
# Agent config
# ---------------------------------------------------------------------------

class TestAgentConfig:
    def test_save_and_get(self):
        db.agent_config_save("r1", "anthropic", "claude-sonnet", "sk-abc123")
        cfg = db.agent_config_get("r1")
        assert cfg is not None
        assert cfg["provider"] == "anthropic"
        assert cfg["model"] == "claude-sonnet"
        assert cfg["api_key"] == "sk-abc123"

    def test_get_missing(self):
        assert db.agent_config_get("nope") is None

    def test_upsert_overwrites(self):
        db.agent_config_save("r1", "anthropic", "old", "key1")
        db.agent_config_save("r1", "openai", "new", "key2")
        cfg = db.agent_config_get("r1")
        assert cfg["provider"] == "openai"
        assert cfg["api_key"] == "key2"

    def test_delete(self):
        db.agent_config_save("r1", "anthropic", "m", "k")
        assert db.agent_config_delete("r1") is True
        assert db.agent_config_get("r1") is None

    def test_delete_missing(self):
        assert db.agent_config_delete("nope") is False

    def test_key_stored_as_base64(self):
        """API keys should not be stored as plaintext."""
        import base64
        db.agent_config_save("r1", "anthropic", "m", "sk-secret")
        conn = db.get_db()
        row = conn.execute("SELECT api_key_b64 FROM agent_configs WHERE repo_id = 'r1'").fetchone()
        raw = row["api_key_b64"]
        # Should be valid base64 that decodes to the original key
        assert base64.b64decode(raw).decode() == "sk-secret"
        # Should NOT be plaintext
        assert raw != "sk-secret"


# ---------------------------------------------------------------------------
# Agent usage
# ---------------------------------------------------------------------------

class TestAgentUsage:
    def test_initial_zero(self):
        u = db.agent_usage_get("r1")
        assert u["requests"] == 0
        assert u["total_tokens"] == 0

    def test_add_accumulates(self):
        db.agent_usage_add("r1", prompt_tokens=100, completion_tokens=50, total_tokens=150)
        db.agent_usage_add("r1", prompt_tokens=200, completion_tokens=100, total_tokens=300)
        u = db.agent_usage_get("r1")
        assert u["requests"] == 2
        assert u["prompt_tokens"] == 300
        assert u["completion_tokens"] == 150
        assert u["total_tokens"] == 450

    def test_reset(self):
        db.agent_usage_add("r1", prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert db.agent_usage_reset("r1") is True
        u = db.agent_usage_get("r1")
        assert u["requests"] == 0


# ---------------------------------------------------------------------------
# Users & sessions
# ---------------------------------------------------------------------------

class TestUsers:
    def test_create_and_verify(self):
        uid = db.user_create("admin", "password123")
        assert uid is not None
        assert db.user_verify("admin", "password123") == uid

    def test_wrong_password(self):
        db.user_create("admin", "correct")
        assert db.user_verify("admin", "wrong") is None

    def test_unknown_user(self):
        assert db.user_verify("ghost", "pass") is None

    def test_user_count(self):
        assert db.user_count() == 0
        db.user_create("a", "pass")
        assert db.user_count() == 1
        db.user_create("b", "pass")
        assert db.user_count() == 2

    def test_duplicate_username(self):
        import sqlite3
        db.user_create("admin", "pass")
        with pytest.raises(sqlite3.IntegrityError):
            db.user_create("admin", "pass2")


class TestSessions:
    def test_create_and_validate(self):
        uid = db.user_create("admin", "pass")
        token = db.session_create(uid)
        assert isinstance(token, str)
        assert len(token) > 20
        info = db.session_validate(token)
        assert info is not None
        assert info["user_id"] == uid
        assert info["username"] == "admin"

    def test_invalid_token(self):
        assert db.session_validate("bogus-token") is None

    def test_delete_session(self):
        uid = db.user_create("admin", "pass")
        token = db.session_create(uid)
        assert db.session_delete(token) is True
        assert db.session_validate(token) is None

    def test_expired_session(self):
        """Manually set an expired session and verify it's rejected."""
        uid = db.user_create("admin", "pass")
        token = db.session_create(uid)
        # Force expiry to the past
        conn = db.get_db()
        conn.execute(
            "UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00' WHERE token = ?",
            (token,),
        )
        conn.commit()
        assert db.session_validate(token) is None

    def test_cleanup(self):
        uid = db.user_create("admin", "pass")
        t1 = db.session_create(uid)
        t2 = db.session_create(uid)
        # Expire t1
        conn = db.get_db()
        conn.execute(
            "UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00' WHERE token = ?",
            (t1,),
        )
        conn.commit()
        removed = db.session_cleanup()
        assert removed == 1
        assert db.session_validate(t1) is None
        assert db.session_validate(t2) is not None
