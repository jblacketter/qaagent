from __future__ import annotations

import pytest

from qaagent.evidence.id_generator import EvidenceIDGenerator


def test_next_id_increments_per_prefix() -> None:
    gen = EvidenceIDGenerator("20251024_193012Z")
    first = gen.next_id("FND")
    second = gen.next_id("FND")
    other = gen.next_id("COV")

    assert first == "FND-20251024-0001"
    assert second == "FND-20251024-0002"
    assert other == "COV-20251024-0001"


def test_prefix_validation() -> None:
    gen = EvidenceIDGenerator("20251024_193012Z")
    with pytest.raises(ValueError):
        gen.next_id("")
    with pytest.raises(ValueError):
        gen.next_id("123")


def test_invalid_run_id_raises() -> None:
    with pytest.raises(ValueError):
        EvidenceIDGenerator("")
    with pytest.raises(ValueError):
        EvidenceIDGenerator("bad_run")
