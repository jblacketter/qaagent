from pathlib import Path
import pytest

pytest.importorskip("yaml")

from qaagent.openapi_utils import enumerate_operations, load_openapi


def test_enumerate_operations_from_yaml():
    spec_path = Path("tests/fixtures/data/openapi_minimal.yaml")
    spec = load_openapi(spec_path.as_posix())
    ops = enumerate_operations(spec)
    methods = {(op.method, op.path) for op in ops}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods
    assert len(ops) == 2
