"""Tests for doc config overrides (DocSettings integration)."""

import pytest
from qaagent.analyzers.models import Route, RouteSource
from qaagent.config.models import DocSettings, DocIntegrationOverride
from qaagent.doc.generator import generate_documentation, _apply_doc_settings
from qaagent.doc.models import FeatureArea, Integration, IntegrationType, RouteDoc


def _make_routes():
    return [
        Route(path="/users", method="GET", auth_required=False, tags=["users"]),
        Route(path="/users", method="POST", auth_required=False, tags=["users"]),
        Route(path="/internal/metrics", method="GET", auth_required=False, tags=["internal"]),
    ]


class TestApplyDocSettings:
    def test_add_new_integration(self):
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(
                    name="PBS",
                    type="http_client",
                    description="Public Broadcasting Service API",
                    env_vars=["PBS_API_KEY"],
                    connected_features=["content"],
                ),
            ],
        )
        integrations: list[Integration] = []
        features = [FeatureArea(id="content", name="Content")]

        result_int, result_feat = _apply_doc_settings(settings, integrations, features)
        assert len(result_int) == 1
        assert result_int[0].name == "PBS"
        assert result_int[0].type == IntegrationType.HTTP_CLIENT
        assert result_int[0].source == "config"
        assert "PBS_API_KEY" in result_int[0].env_vars

    def test_merge_existing_integration(self):
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(
                    name="Redis",
                    description="Custom Redis description",
                    env_vars=["REDIS_CUSTOM"],
                    connected_features=["cache"],
                ),
            ],
        )
        integrations = [
            Integration(
                id="redis",
                name="Redis",
                type=IntegrationType.DATABASE,
                package="redis",
                env_vars=["REDIS_URL"],
            ),
        ]
        features = [FeatureArea(id="cache", name="Cache")]

        result_int, _ = _apply_doc_settings(settings, integrations, features)
        assert len(result_int) == 1
        redis = result_int[0]
        assert redis.description == "Custom Redis description"
        assert "REDIS_URL" in redis.env_vars
        assert "REDIS_CUSTOM" in redis.env_vars
        assert redis.connected_features == ["cache"]
        assert redis.source == "config"

    def test_exclude_features(self):
        settings = DocSettings(exclude_features=["internal-*"])
        integrations: list[Integration] = []
        features = [
            FeatureArea(id="users", name="Users"),
            FeatureArea(id="internal-metrics", name="Internal Metrics"),
            FeatureArea(id="internal-health", name="Internal Health"),
        ]

        _, result_feat = _apply_doc_settings(settings, integrations, features)
        assert len(result_feat) == 1
        assert result_feat[0].id == "users"

    def test_exclude_exact_match(self):
        settings = DocSettings(exclude_features=["health"])
        integrations: list[Integration] = []
        features = [
            FeatureArea(id="users", name="Users"),
            FeatureArea(id="health", name="Health"),
        ]

        _, result_feat = _apply_doc_settings(settings, integrations, features)
        assert len(result_feat) == 1
        assert result_feat[0].id == "users"

    def test_no_settings_is_noop(self):
        integrations = [Integration(id="redis", name="Redis", type=IntegrationType.DATABASE)]
        features = [FeatureArea(id="users", name="Users")]

        result_int, result_feat = _apply_doc_settings(None, integrations, features)
        assert len(result_int) == 1
        assert len(result_feat) == 1

    def test_unknown_type_defaults(self):
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(
                    name="Custom Service",
                    type="not_a_real_type",
                ),
            ],
        )
        result_int, _ = _apply_doc_settings(settings, [], [])
        assert result_int[0].type == IntegrationType.UNKNOWN

    def test_duplicate_config_overrides_merge(self):
        """Repeated overrides with the same name should merge, not duplicate."""
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(name="Redis", type="database", env_vars=["REDIS_URL"]),
                DocIntegrationOverride(name="Redis", type="database", env_vars=["REDIS_PASS"]),
            ],
        )
        result_int, _ = _apply_doc_settings(settings, [], [])
        redis_entries = [i for i in result_int if i.id == "redis"]
        assert len(redis_entries) == 1, f"Expected 1 Redis entry, got {len(redis_entries)}"
        assert "REDIS_URL" in redis_entries[0].env_vars
        assert "REDIS_PASS" in redis_entries[0].env_vars


class TestGenerateWithDocSettings:
    def test_custom_summary(self):
        settings = DocSettings(custom_summary="This is a custom app summary.")
        doc = generate_documentation(
            routes=_make_routes(),
            app_name="Test",
            use_llm=False,
            doc_settings=settings,
        )
        assert doc.summary == "This is a custom app summary."

    def test_integration_override_in_generate(self):
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(
                    name="Ethos",
                    type="sdk",
                    description="Ethics compliance",
                    env_vars=["ETHOS_TOKEN"],
                ),
            ],
        )
        doc = generate_documentation(
            routes=_make_routes(),
            app_name="Test",
            use_llm=False,
            doc_settings=settings,
        )
        assert any(i.name == "Ethos" for i in doc.integrations)

    def test_exclude_in_generate(self):
        settings = DocSettings(exclude_features=["internal"])
        doc = generate_documentation(
            routes=_make_routes(),
            app_name="Test",
            use_llm=False,
            doc_settings=settings,
        )
        assert not any(f.id == "internal" for f in doc.features)
        assert any(f.id == "users" for f in doc.features)

    def test_no_doc_settings(self):
        doc = generate_documentation(
            routes=_make_routes(),
            app_name="Test",
            use_llm=False,
        )
        # Should work fine without settings
        assert doc.app_name == "Test"


class TestDocSettingsModel:
    def test_default_settings(self):
        settings = DocSettings()
        assert settings.integrations == []
        assert settings.exclude_features == []
        assert settings.custom_summary is None

    def test_full_settings(self):
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(
                    name="PBS",
                    type="http_client",
                    env_vars=["PBS_KEY"],
                    connected_features=["content"],
                ),
            ],
            exclude_features=["internal-*"],
            custom_summary="My custom summary.",
        )
        assert len(settings.integrations) == 1
        assert settings.integrations[0].name == "PBS"
        assert settings.exclude_features == ["internal-*"]

    def test_roundtrip(self):
        settings = DocSettings(
            integrations=[
                DocIntegrationOverride(name="Test", type="sdk"),
            ],
            exclude_features=["debug-*"],
        )
        data = settings.model_dump()
        settings2 = DocSettings.model_validate(data)
        assert len(settings2.integrations) == 1
        assert settings2.exclude_features == ["debug-*"]
