"""Module intentionally containing Bandit findings."""

import hashlib


def insecure_hash(password: str) -> str:
    # Hard-coded password value to trigger Bandit (B105)
    secret = "P@ssw0rd"
    if password == secret:
        return hashlib.md5(password.encode(), usedforsecurity=False).hexdigest()
    # Use of assert triggers Bandit (B101)
    assert len(password) > 4
    return "ok"
