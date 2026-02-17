"""Backward-compatibility test for pre-Phase 19 appdoc.json payloads (Phase 19)."""

from __future__ import annotations

import json
from pathlib import Path

from qaagent.doc.models import AppDocumentation
from qaagent.doc.generator import load_documentation, save_documentation


# Minimal payload representing a pre-Phase 19 appdoc.json (no new fields)
_LEGACY_PAYLOAD = {
    "app_name": "legacy-app",
    "summary": "A legacy application.",
    "generated_at": "2026-01-01T00:00:00",
    "content_hash": "abc123",
    "source_dir": "/some/path",
    "features": [
        {
            "id": "feat-1",
            "name": "Feature One",
            "description": "First feature.",
            "routes": [{"path": "/api/items", "method": "GET"}],
            "crud_operations": ["read"],
            "auth_required": False,
            "integration_ids": [],
            "tags": [],
        }
    ],
    "integrations": [],
    "discovered_cujs": [],
    "architecture_nodes": [],
    "architecture_edges": [],
    "total_routes": 1,
    "metadata": {"version": "pre-phase19"},
}


class TestLegacyPayloadCompat:
    def test_model_validate_legacy_payload(self):
        """AppDocumentation.model_validate loads a payload without Phase 19 fields."""
        doc = AppDocumentation.model_validate(_LEGACY_PAYLOAD)
        # Existing fields preserved
        assert doc.app_name == "legacy-app"
        assert doc.summary == "A legacy application."
        assert len(doc.features) == 1
        assert doc.total_routes == 1
        assert doc.metadata == {"version": "pre-phase19"}
        # New fields take defaults
        assert doc.app_overview == ""
        assert doc.tech_stack == []
        assert doc.user_roles == []
        assert doc.user_journeys == []

    def test_load_documentation_legacy_file(self, tmp_path: Path):
        """load_documentation() successfully loads a pre-Phase 19 appdoc.json file."""
        qaagent_dir = tmp_path / ".qaagent"
        qaagent_dir.mkdir()
        (qaagent_dir / "appdoc.json").write_text(
            json.dumps(_LEGACY_PAYLOAD), encoding="utf-8"
        )
        doc = load_documentation(tmp_path)
        assert doc is not None
        assert doc.app_name == "legacy-app"
        assert doc.app_overview == ""
        assert doc.tech_stack == []
        assert doc.user_roles == []
        assert doc.user_journeys == []

    def test_save_then_load_roundtrip(self, tmp_path: Path):
        """A doc saved with Phase 19 fields loads correctly."""
        from qaagent.doc.models import UserRole, UserJourney, JourneyStep

        doc = AppDocumentation(
            app_name="roundtrip-app",
            total_routes=5,
            app_overview="A test overview.",
            tech_stack=["Python", "FastAPI"],
            user_roles=[UserRole(id="user", name="User", description="End user")],
            user_journeys=[UserJourney(
                id="j1", name="Login", actor="user",
                steps=[JourneyStep(order=1, action="Log in", expected_outcome="Authenticated")],
            )],
        )
        save_documentation(doc, tmp_path)
        loaded = load_documentation(tmp_path)
        assert loaded is not None
        assert loaded.app_overview == "A test overview."
        assert loaded.tech_stack == ["Python", "FastAPI"]
        assert len(loaded.user_roles) == 1
        assert loaded.user_roles[0].name == "User"
        assert len(loaded.user_journeys) == 1
        assert loaded.user_journeys[0].steps[0].action == "Log in"
