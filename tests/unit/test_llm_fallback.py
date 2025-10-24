from pathlib import Path

from qaagent.llm import generate_api_tests_from_spec
from qaagent.openapi_utils import load_openapi


def test_generate_api_tests_fallback_works_without_llm():
    spec = load_openapi("tests/fixtures/data/openapi_minimal.yaml")
    code = generate_api_tests_from_spec(spec, base_url="http://localhost:8000", max_tests=2)
    assert "def test_" in code
    assert "httpx" in code
