"""SQLite persistence layer for QA Agent.

Provides a thin wrapper around stdlib sqlite3 for persisting:
- Repositories (replaces in-memory dict)
- Agent configurations and usage counters
- Users and sessions (authentication)

Zero external dependencies — uses only the Python standard library.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_connection: Optional[sqlite3.Connection] = None
_db_path: Optional[str] = None


def _default_db_path() -> str:
    """Return default database path: ~/.qaagent/qaagent.db"""
    qaagent_dir = Path.home() / ".qaagent"
    qaagent_dir.mkdir(parents=True, exist_ok=True)
    return str(qaagent_dir / "qaagent.db")


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a singleton SQLite connection (thread-safe).

    On first call (or after reset_connection), opens the database,
    enables WAL mode and foreign keys, and runs migrations.
    """
    global _connection, _db_path

    with _lock:
        if _connection is not None:
            return _connection

        resolved = db_path or _db_path or _default_db_path()
        _db_path = resolved

        conn = sqlite3.connect(resolved, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _connection = conn
        _run_migrations(conn)
        return conn


def reset_connection() -> None:
    """Close and discard the singleton connection (for test isolation)."""
    global _connection, _db_path

    with _lock:
        if _connection is not None:
            _connection.close()
        _connection = None
        _db_path = None


def set_db_path(path: str) -> None:
    """Pre-set the database path before first get_db() call."""
    global _db_path
    _db_path = path


# ---------------------------------------------------------------------------
# Schema migrations
# ---------------------------------------------------------------------------

def _run_migrations(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS repositories (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            path        TEXT NOT NULL,
            repo_type   TEXT NOT NULL DEFAULT 'local',
            last_scan   TEXT,
            status      TEXT NOT NULL DEFAULT 'ready',
            run_count   INTEGER NOT NULL DEFAULT 0,
            analysis_options TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS agent_configs (
            repo_id     TEXT PRIMARY KEY,
            provider    TEXT NOT NULL DEFAULT 'anthropic',
            model       TEXT NOT NULL DEFAULT 'claude-sonnet-4-5-20250929',
            api_key_b64 TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS agent_usage (
            repo_id           TEXT PRIMARY KEY,
            requests          INTEGER NOT NULL DEFAULT 0,
            prompt_tokens     INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens      INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt          TEXT NOT NULL,
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
    """)


# ---------------------------------------------------------------------------
# Repository CRUD
# ---------------------------------------------------------------------------

def repo_upsert(
    repo_id: str,
    name: str,
    path: str,
    repo_type: str = "local",
    status: str = "ready",
    run_count: int = 0,
    last_scan: Optional[str] = None,
    analysis_options: Optional[dict] = None,
) -> None:
    conn = get_db()
    conn.execute(
        """INSERT INTO repositories (id, name, path, repo_type, status, run_count, last_scan, analysis_options)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               name=excluded.name,
               path=excluded.path,
               repo_type=excluded.repo_type,
               status=excluded.status,
               run_count=excluded.run_count,
               last_scan=excluded.last_scan,
               analysis_options=excluded.analysis_options""",
        (repo_id, name, path, repo_type, status, run_count, last_scan,
         json.dumps(analysis_options or {})),
    )
    conn.commit()


def repo_get(repo_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
    if row is None:
        return None
    return _row_to_repo(row)


def repo_list() -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM repositories ORDER BY name").fetchall()
    return [_row_to_repo(r) for r in rows]


def repo_delete(repo_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
    conn.commit()
    return cur.rowcount > 0


def repo_update_status(repo_id: str, status: str, last_scan: Optional[str] = None, run_count: Optional[int] = None) -> None:
    conn = get_db()
    parts = ["status = ?"]
    params: list = [status]
    if last_scan is not None:
        parts.append("last_scan = ?")
        params.append(last_scan)
    if run_count is not None:
        parts.append("run_count = ?")
        params.append(run_count)
    params.append(repo_id)
    conn.execute(f"UPDATE repositories SET {', '.join(parts)} WHERE id = ?", params)
    conn.commit()


def _row_to_repo(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "path": row["path"],
        "repo_type": row["repo_type"],
        "last_scan": row["last_scan"],
        "status": row["status"],
        "run_count": row["run_count"],
        "analysis_options": json.loads(row["analysis_options"]),
    }


# ---------------------------------------------------------------------------
# Agent config helpers
# ---------------------------------------------------------------------------

def _encode_key(key: str) -> str:
    """Encode an API key as base64 (prevents casual plaintext exposure)."""
    if not key:
        return ""
    return base64.b64encode(key.encode("utf-8")).decode("ascii")


def _decode_key(b64: str) -> str:
    if not b64:
        return ""
    return base64.b64decode(b64.encode("ascii")).decode("utf-8")


def agent_config_save(repo_id: str, provider: str, model: str, api_key: str) -> None:
    conn = get_db()
    conn.execute(
        """INSERT INTO agent_configs (repo_id, provider, model, api_key_b64)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(repo_id) DO UPDATE SET
               provider=excluded.provider,
               model=excluded.model,
               api_key_b64=excluded.api_key_b64""",
        (repo_id, provider, model, _encode_key(api_key)),
    )
    conn.commit()


def agent_config_get(repo_id: str) -> Optional[Dict[str, str]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM agent_configs WHERE repo_id = ?", (repo_id,)).fetchone()
    if row is None:
        return None
    return {
        "repo_id": row["repo_id"],
        "provider": row["provider"],
        "model": row["model"],
        "api_key": _decode_key(row["api_key_b64"]),
    }


def agent_config_delete(repo_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM agent_configs WHERE repo_id = ?", (repo_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Agent usage helpers
# ---------------------------------------------------------------------------

def agent_usage_get(repo_id: str) -> Dict[str, Any]:
    conn = get_db()
    row = conn.execute("SELECT * FROM agent_usage WHERE repo_id = ?", (repo_id,)).fetchone()
    if row is None:
        return {"repo_id": repo_id, "requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "repo_id": row["repo_id"],
        "requests": row["requests"],
        "prompt_tokens": row["prompt_tokens"],
        "completion_tokens": row["completion_tokens"],
        "total_tokens": row["total_tokens"],
    }


def agent_usage_add(repo_id: str, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> None:
    conn = get_db()
    conn.execute(
        """INSERT INTO agent_usage (repo_id, requests, prompt_tokens, completion_tokens, total_tokens)
           VALUES (?, 1, ?, ?, ?)
           ON CONFLICT(repo_id) DO UPDATE SET
               requests = requests + 1,
               prompt_tokens = prompt_tokens + excluded.prompt_tokens,
               completion_tokens = completion_tokens + excluded.completion_tokens,
               total_tokens = total_tokens + excluded.total_tokens""",
        (repo_id, prompt_tokens, completion_tokens, total_tokens),
    )
    conn.commit()


def agent_usage_reset(repo_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM agent_usage WHERE repo_id = ?", (repo_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# User helpers (authentication)
# ---------------------------------------------------------------------------

_PBKDF2_ITERATIONS = 600_000


def _hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """Hash a password with PBKDF2-SHA256. Returns (hex_hash, hex_salt)."""
    if salt is None:
        salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return dk.hex(), salt.hex()


def user_count() -> int:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    return row["cnt"]


def user_create(username: str, password: str) -> int:
    """Create a user. Returns user id. Raises sqlite3.IntegrityError on duplicate."""
    hash_hex, salt_hex = _hash_password(password)
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
        (username, hash_hex, salt_hex, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def user_verify(username: str, password: str) -> Optional[int]:
    """Verify credentials. Returns user_id on success, None on failure."""
    conn = get_db()
    row = conn.execute("SELECT id, password_hash, salt FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        return None
    expected_hash = row["password_hash"]
    salt = bytes.fromhex(row["salt"])
    computed_hash, _ = _hash_password(password, salt)
    if not secrets.compare_digest(computed_hash, expected_hash):
        return None
    return row["id"]


def user_change_password(username: str, old_password: str, new_password: str) -> bool:
    """Change a user's password. Returns True on success, False if old password is wrong."""
    user_id = user_verify(username, old_password)
    if user_id is None:
        return False
    new_hash, new_salt = _hash_password(new_password)
    conn = get_db()
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (new_hash, new_salt, user_id),
    )
    conn.commit()
    return True


def user_get_first_username() -> Optional[str]:
    """Return the username of the first user (admin), or None if no users."""
    conn = get_db()
    row = conn.execute("SELECT username FROM users ORDER BY id LIMIT 1").fetchone()
    return row["username"] if row else None


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

_SESSION_LIFETIME_HOURS = 24


def session_create(user_id: int) -> str:
    """Create a new session token for a user. Returns the token."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=_SESSION_LIFETIME_HOURS)
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now.isoformat(), expires.isoformat()),
    )
    conn.commit()
    return token


def session_validate(token: str) -> Optional[Dict[str, Any]]:
    """Validate a session token. Returns {user_id, username} or None."""
    conn = get_db()
    row = conn.execute(
        """SELECT s.user_id, s.expires_at, u.username
           FROM sessions s JOIN users u ON s.user_id = u.id
           WHERE s.token = ?""",
        (token,),
    ).fetchone()
    if row is None:
        return None
    expires = datetime.fromisoformat(row["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        # Expired — clean it up
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return None
    return {"user_id": row["user_id"], "username": row["username"]}


def session_delete(token: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    return cur.rowcount > 0


def session_cleanup() -> int:
    """Remove all expired sessions. Returns count deleted."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.commit()
    return cur.rowcount
