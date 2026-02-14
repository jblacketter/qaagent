"""Tests for integration detection."""

import json
import pytest
from pathlib import Path

from qaagent.doc.integration_detector import IntegrationDetector, IntegrationType


@pytest.fixture
def tmp_source(tmp_path):
    """Create a temporary source directory for test files."""
    src = tmp_path / "src"
    src.mkdir()
    return src


class TestPythonImportDetection:
    def test_detects_requests(self, tmp_source):
        (tmp_source / "client.py").write_text("import requests\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 1
        assert integrations[0].name == "Requests HTTP"
        assert integrations[0].type == IntegrationType.HTTP_CLIENT
        assert integrations[0].package == "requests"

    def test_detects_from_import(self, tmp_source):
        (tmp_source / "db.py").write_text("from sqlalchemy import create_engine\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "SQLAlchemy" for i in integrations)

    def test_detects_boto3(self, tmp_source):
        (tmp_source / "aws.py").write_text("import boto3\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "AWS (boto3)" and i.type == IntegrationType.SDK for i in integrations)

    def test_detects_stripe(self, tmp_source):
        (tmp_source / "pay.py").write_text("import stripe\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Stripe" and i.type == IntegrationType.SDK for i in integrations)

    def test_detects_redis(self, tmp_source):
        (tmp_source / "cache.py").write_text("import redis\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Redis" and i.type == IntegrationType.DATABASE for i in integrations)

    def test_detects_nested_import(self, tmp_source):
        (tmp_source / "storage.py").write_text(
            "from google.cloud.storage import Client\n"
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Google Cloud Storage" for i in integrations)

    def test_multiple_imports(self, tmp_source):
        (tmp_source / "app.py").write_text(
            "import requests\nimport redis\nimport stripe\n"
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        names = {i.name for i in integrations}
        assert "Requests HTTP" in names
        assert "Redis" in names
        assert "Stripe" in names

    def test_ignores_unknown_imports(self, tmp_source):
        (tmp_source / "app.py").write_text("import os\nimport sys\nimport json\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 0

    def test_handles_syntax_error(self, tmp_source):
        (tmp_source / "bad.py").write_text("def broken(\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 0


class TestEnvVarDetection:
    def test_os_environ_subscript(self, tmp_source):
        (tmp_source / "config.py").write_text(
            'import os\nkey = os.environ["STRIPE_API_KEY"]\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(
            i.name == "Stripe" and "STRIPE_API_KEY" in i.env_vars
            for i in integrations
        )

    def test_os_environ_get(self, tmp_source):
        (tmp_source / "config.py").write_text(
            'import os\nurl = os.environ.get("REDIS_URL")\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(
            i.name == "Redis" and "REDIS_URL" in i.env_vars
            for i in integrations
        )

    def test_os_getenv(self, tmp_source):
        (tmp_source / "config.py").write_text(
            'import os\ndb = os.getenv("DATABASE_URL")\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(
            i.name == "Database" and "DATABASE_URL" in i.env_vars
            for i in integrations
        )

    def test_aws_env_vars(self, tmp_source):
        (tmp_source / "config.py").write_text(
            'import os\nkey = os.environ["AWS_ACCESS_KEY_ID"]\nsecret = os.environ["AWS_SECRET_ACCESS_KEY"]\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        aws = next((i for i in integrations if i.name == "AWS"), None)
        assert aws is not None
        assert "AWS_ACCESS_KEY_ID" in aws.env_vars
        assert "AWS_SECRET_ACCESS_KEY" in aws.env_vars

    def test_pbs_env_var(self, tmp_source):
        (tmp_source / "config.py").write_text(
            'import os\nkey = os.environ["PBS_API_KEY"]\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "PBS" for i in integrations)

    def test_ethos_env_var(self, tmp_source):
        (tmp_source / "config.py").write_text(
            'import os\ntoken = os.environ["ETHOS_TOKEN"]\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Ethos" for i in integrations)

    def test_process_env_in_python(self, tmp_source):
        # Mixed codebases may have process.env patterns in Python strings
        (tmp_source / "config.py").write_text(
            '# Config reference: process.env.STRIPE_SECRET_KEY\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Stripe" for i in integrations)


class TestJsEnvVarDetection:
    def test_process_env(self, tmp_source):
        (tmp_source / "config.ts").write_text(
            "const key = process.env.STRIPE_SECRET_KEY;\n"
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Stripe" for i in integrations)

    def test_multiple_env_vars(self, tmp_source):
        (tmp_source / "config.js").write_text(
            "const a = process.env.AWS_REGION;\nconst b = process.env.REDIS_URL;\n"
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        names = {i.name for i in integrations}
        assert "AWS" in names
        assert "Redis" in names


class TestPackageJsonDetection:
    def test_detects_axios(self, tmp_source):
        pkg = {"dependencies": {"axios": "^1.0.0"}}
        (tmp_source / "package.json").write_text(json.dumps(pkg))
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Axios HTTP" for i in integrations)

    def test_detects_prisma(self, tmp_source):
        pkg = {"dependencies": {"@prisma/client": "^5.0.0"}}
        (tmp_source / "package.json").write_text(json.dumps(pkg))
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Prisma" for i in integrations)

    def test_detects_dev_dependency(self, tmp_source):
        pkg = {"devDependencies": {"@sentry/node": "^7.0.0"}}
        (tmp_source / "package.json").write_text(json.dumps(pkg))
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert any(i.name == "Sentry" for i in integrations)

    def test_handles_invalid_json(self, tmp_source):
        (tmp_source / "package.json").write_text("not json")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 0


class TestMerging:
    def test_merges_import_and_env_var(self, tmp_source):
        (tmp_source / "app.py").write_text(
            'import stripe\nimport os\nkey = os.environ["STRIPE_API_KEY"]\n'
        )
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        stripe_int = next(i for i in integrations if i.name == "Stripe")
        assert stripe_int.package == "stripe"
        assert "STRIPE_API_KEY" in stripe_int.env_vars


class TestEdgeCases:
    def test_nonexistent_directory(self, tmp_path):
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_path / "nonexistent")
        assert integrations == []

    def test_empty_directory(self, tmp_source):
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert integrations == []

    def test_skips_node_modules(self, tmp_source):
        nm = tmp_source / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("const x = process.env.STRIPE_KEY;\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 0

    def test_skips_virtualenv(self, tmp_source):
        """Python files inside .venv should not be scanned."""
        venv = tmp_source / ".venv" / "lib" / "python3.11" / "site-packages" / "pkg"
        venv.mkdir(parents=True)
        (venv / "mod.py").write_text("import stripe\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 0

    def test_skips_pycache(self, tmp_source):
        """Python files inside __pycache__ should not be scanned."""
        cache = tmp_source / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "client.py").write_text("import boto3\n")
        detector = IntegrationDetector()
        integrations = detector.detect(tmp_source)
        assert len(integrations) == 0
