"""Tests for markdown export."""

import pytest
from qaagent.doc.markdown_export import render_markdown
from qaagent.doc.models import (
    AppDocumentation,
    CujStep,
    DiscoveredCUJ,
    FeatureArea,
    Integration,
    IntegrationType,
    RouteDoc,
)


class TestRenderMarkdown:
    def test_minimal_doc(self):
        doc = AppDocumentation(app_name="Test App")
        md = render_markdown(doc)
        assert "# Test App Documentation" in md
        assert "Generated at" in md

    def test_summary_section(self):
        doc = AppDocumentation(app_name="My App", summary="This is a test app.")
        md = render_markdown(doc)
        assert "## Summary" in md
        assert "This is a test app." in md

    def test_features_section(self):
        doc = AppDocumentation(
            app_name="App",
            features=[
                FeatureArea(
                    id="users",
                    name="Users",
                    description="User management",
                    crud_operations=["create", "read"],
                    auth_required=True,
                    routes=[
                        RouteDoc(
                            path="/users",
                            method="GET",
                            auth_required=True,
                            summary="List users",
                        ),
                        RouteDoc(
                            path="/users",
                            method="POST",
                            auth_required=True,
                            summary="Create user",
                        ),
                    ],
                ),
            ],
        )
        md = render_markdown(doc)
        assert "## Features" in md
        assert "### Users" in md
        assert "Auth Required" in md
        assert "CRUD: CREATE, READ" in md
        assert "| GET | `/users` | Yes | List users |" in md
        assert "| POST | `/users` | Yes | Create user |" in md
        assert "User management" in md

    def test_integrations_section(self):
        doc = AppDocumentation(
            app_name="App",
            integrations=[
                Integration(
                    id="stripe",
                    name="Stripe",
                    type=IntegrationType.SDK,
                    package="stripe",
                    env_vars=["STRIPE_API_KEY"],
                    connected_features=["payments"],
                    description="Payment processing.",
                ),
            ],
        )
        md = render_markdown(doc)
        assert "## External Integrations" in md
        assert "### Stripe" in md
        assert "**Type**: sdk" in md
        assert "**Package**: `stripe`" in md
        assert "`STRIPE_API_KEY`" in md
        assert "**Connected Features**: payments" in md
        assert "Payment processing." in md

    def test_cujs_section(self):
        doc = AppDocumentation(
            app_name="App",
            discovered_cujs=[
                DiscoveredCUJ(
                    id="login-flow",
                    name="Login Flow",
                    description="User authentication journey",
                    steps=[
                        CujStep(order=1, action="Register", route="/register", method="POST"),
                        CujStep(order=2, action="Login", route="/login", method="POST"),
                        CujStep(order=3, action="Access dashboard", route="/dashboard", method="GET"),
                    ],
                ),
            ],
        )
        md = render_markdown(doc)
        assert "## Critical User Journeys" in md
        assert "### Login Flow" in md
        assert "User authentication journey" in md
        assert "1. Register (`POST /register`)" in md
        assert "2. Login (`POST /login`)" in md
        assert "3. Access dashboard (`GET /dashboard`)" in md

    def test_metadata_footer(self):
        doc = AppDocumentation(
            app_name="App",
            total_routes=42,
            content_hash="abc123",
        )
        md = render_markdown(doc)
        assert "42 routes" in md
        assert "abc123" in md

    def test_full_doc(self):
        doc = AppDocumentation(
            app_name="Full App",
            summary="A comprehensive app.",
            total_routes=10,
            content_hash="hash123",
            features=[
                FeatureArea(
                    id="users",
                    name="Users",
                    routes=[RouteDoc(path="/users", method="GET")],
                ),
            ],
            integrations=[
                Integration(id="redis", name="Redis", type=IntegrationType.DATABASE),
            ],
            discovered_cujs=[
                DiscoveredCUJ(
                    id="flow",
                    name="Main Flow",
                    steps=[CujStep(order=1, action="Start")],
                ),
            ],
        )
        md = render_markdown(doc)
        # All sections present
        assert "# Full App Documentation" in md
        assert "## Summary" in md
        assert "## Features" in md
        assert "## External Integrations" in md
        assert "## Critical User Journeys" in md

    def test_no_features_or_integrations(self):
        doc = AppDocumentation(app_name="Empty")
        md = render_markdown(doc)
        assert "## Features" not in md
        assert "## External Integrations" not in md
        assert "## Critical User Journeys" not in md

    def test_route_without_summary(self):
        doc = AppDocumentation(
            app_name="App",
            features=[
                FeatureArea(
                    id="test",
                    name="Test",
                    routes=[RouteDoc(path="/test", method="GET")],
                ),
            ],
        )
        md = render_markdown(doc)
        assert "| GET | `/test` | No | - |" in md

    def test_cuj_step_without_route(self):
        doc = AppDocumentation(
            app_name="App",
            discovered_cujs=[
                DiscoveredCUJ(
                    id="flow",
                    name="Flow",
                    steps=[CujStep(order=1, action="Click button")],
                ),
            ],
        )
        md = render_markdown(doc)
        assert "1. Click button" in md
        assert "`" not in md.split("1. Click button")[1].split("\n")[0]
