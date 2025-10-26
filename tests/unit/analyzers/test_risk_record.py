from __future__ import annotations

import pytest

from qaagent.evidence.models import RiskRecord


def test_risk_record_to_dict_contains_fields() -> None:
    record = RiskRecord(
        risk_id="RSK-20251025-0001",
        component="src/auth/login.py",
        score=82.5,
        band="P0",
        confidence=0.75,
        severity="critical",
        title="High-risk auth module",
        description="Multiple high severity issues detected.",
        evidence_refs=["FND-1", "CHN-2"],
        factors={"security": 60.0, "churn": 22.5},
        recommendations=["Add authentication checks", "Increase test coverage"],
    )

    payload = record.to_dict()
    assert payload["risk_id"] == "RSK-20251025-0001"
    assert payload["score"] == 82.5
    assert payload["band"] == "P0"
    assert payload["factors"]["security"] == 60.0


def test_risk_record_validation() -> None:
    with pytest.raises(ValueError):
        RiskRecord(
            risk_id="RSK-1",
            component="src",
            score=120.0,
            band="P0",
            confidence=0.5,
            severity="critical",
            title="bad",
            description="bad",
        )

    with pytest.raises(ValueError):
        RiskRecord(
            risk_id="RSK-1",
            component="src",
            score=50.0,
            band="P2",
            confidence=1.5,
            severity="high",
            title="bad",
            description="bad",
        )
