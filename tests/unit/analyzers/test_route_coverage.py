from pathlib import Path

from qaagent.analyzers.models import Route
from qaagent.analyzers.route_coverage import build_route_coverage, normalize_path


def test_normalize_path_templates_dynamic_segments():
    assert normalize_path("/users/123/") == "/users/{param}"
    assert normalize_path("/orders/550e8400-e29b-41d4-a716-446655440000/items") == "/orders/{param}/items"
    assert normalize_path("/api/:id") == "/api/{param}"


def test_build_route_coverage_from_openapi_and_junit_fixture():
    root = Path.cwd()
    summary = build_route_coverage(
        openapi_path=str(root / "tests/fixtures/data/openapi.yaml"),
        junit_files=[root / "tests/fixtures/data/junit_schemathesis.xml"],
    )

    assert summary is not None
    assert summary["total"] == 2
    assert summary["covered"] == 1
    assert summary["pct"] == 50.0
    assert ("POST", "/users") in summary["uncovered_samples"]


def test_build_route_coverage_accepts_route_hints_with_path_normalization():
    routes = [
        Route(path="/users/{id}", method="GET", auth_required=False),
    ]
    summary = build_route_coverage(
        routes=routes,
        case_names=[],
        route_hints=[("GET", "/users/42")],
    )

    assert summary is not None
    assert summary["total"] == 1
    assert summary["covered"] == 1
    assert summary["uncovered"] == []


def test_priority_metadata_is_deterministic():
    routes = [
        Route(path="/public/health", method="GET", auth_required=False),
        Route(path="/admin/users", method="GET", auth_required=True, tags=["admin"]),
        Route(path="/users", method="POST", auth_required=False),
    ]
    summary = build_route_coverage(routes=routes, case_names=[])

    assert summary is not None
    uncovered = summary["uncovered"]
    assert uncovered[0]["method"] == "GET"
    assert uncovered[0]["path"] == "/admin/users"
    assert uncovered[0]["priority"] == "high"
    assert uncovered[1]["priority"] in {"high", "medium"}
