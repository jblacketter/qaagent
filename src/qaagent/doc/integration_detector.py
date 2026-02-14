"""AST-based detection of external service integrations."""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import Integration, IntegrationType

# Registry: package import name → (integration name, type)
PACKAGE_REGISTRY: Dict[str, tuple[str, IntegrationType]] = {
    # HTTP clients
    "requests": ("Requests HTTP", IntegrationType.HTTP_CLIENT),
    "httpx": ("HTTPX", IntegrationType.HTTP_CLIENT),
    "aiohttp": ("aiohttp", IntegrationType.HTTP_CLIENT),
    "urllib3": ("urllib3", IntegrationType.HTTP_CLIENT),
    # AWS
    "boto3": ("AWS (boto3)", IntegrationType.SDK),
    "botocore": ("AWS (botocore)", IntegrationType.SDK),
    # Databases
    "psycopg2": ("PostgreSQL", IntegrationType.DATABASE),
    "asyncpg": ("PostgreSQL (async)", IntegrationType.DATABASE),
    "pymongo": ("MongoDB", IntegrationType.DATABASE),
    "motor": ("MongoDB (async)", IntegrationType.DATABASE),
    "sqlalchemy": ("SQLAlchemy", IntegrationType.DATABASE),
    "redis": ("Redis", IntegrationType.DATABASE),
    "aioredis": ("Redis (async)", IntegrationType.DATABASE),
    "mysql": ("MySQL", IntegrationType.DATABASE),
    "pymysql": ("MySQL", IntegrationType.DATABASE),
    "sqlite3": ("SQLite", IntegrationType.DATABASE),
    "elasticsearch": ("Elasticsearch", IntegrationType.DATABASE),
    # Message queues
    "celery": ("Celery", IntegrationType.MESSAGE_QUEUE),
    "kombu": ("Kombu (AMQP)", IntegrationType.MESSAGE_QUEUE),
    "pika": ("RabbitMQ", IntegrationType.MESSAGE_QUEUE),
    "kafka": ("Kafka", IntegrationType.MESSAGE_QUEUE),
    # Storage
    "minio": ("MinIO", IntegrationType.STORAGE),
    "google.cloud.storage": ("Google Cloud Storage", IntegrationType.STORAGE),
    # Auth providers
    "authlib": ("AuthLib", IntegrationType.AUTH_PROVIDER),
    "python_jose": ("JOSE/JWT", IntegrationType.AUTH_PROVIDER),
    "jose": ("JOSE/JWT", IntegrationType.AUTH_PROVIDER),
    "passlib": ("Passlib", IntegrationType.AUTH_PROVIDER),
    "bcrypt": ("bcrypt", IntegrationType.AUTH_PROVIDER),
    # Payment / SaaS SDKs
    "stripe": ("Stripe", IntegrationType.SDK),
    "twilio": ("Twilio", IntegrationType.SDK),
    "sendgrid": ("SendGrid", IntegrationType.SDK),
    "sentry_sdk": ("Sentry", IntegrationType.SDK),
    "slack_sdk": ("Slack", IntegrationType.SDK),
    # Google
    "google.auth": ("Google Auth", IntegrationType.AUTH_PROVIDER),
    "google.cloud": ("Google Cloud", IntegrationType.SDK),
    "firebase_admin": ("Firebase", IntegrationType.SDK),
}

# Env var prefix → (integration name, type)
ENV_VAR_PATTERNS: Dict[str, tuple[str, IntegrationType]] = {
    "STRIPE_": ("Stripe", IntegrationType.SDK),
    "AWS_": ("AWS", IntegrationType.SDK),
    "REDIS_": ("Redis", IntegrationType.DATABASE),
    "DATABASE_URL": ("Database", IntegrationType.DATABASE),
    "DB_": ("Database", IntegrationType.DATABASE),
    "MONGO": ("MongoDB", IntegrationType.DATABASE),
    "POSTGRES": ("PostgreSQL", IntegrationType.DATABASE),
    "MYSQL": ("MySQL", IntegrationType.DATABASE),
    "SENDGRID_": ("SendGrid", IntegrationType.SDK),
    "TWILIO_": ("Twilio", IntegrationType.SDK),
    "SENTRY_": ("Sentry", IntegrationType.SDK),
    "SLACK_": ("Slack", IntegrationType.SDK),
    "FIREBASE_": ("Firebase", IntegrationType.SDK),
    "GOOGLE_": ("Google Cloud", IntegrationType.SDK),
    "RABBITMQ_": ("RabbitMQ", IntegrationType.MESSAGE_QUEUE),
    "KAFKA_": ("Kafka", IntegrationType.MESSAGE_QUEUE),
    "CELERY_": ("Celery", IntegrationType.MESSAGE_QUEUE),
    "ELASTICSEARCH_": ("Elasticsearch", IntegrationType.DATABASE),
    "S3_": ("AWS S3", IntegrationType.STORAGE),
    "MINIO_": ("MinIO", IntegrationType.STORAGE),
    "PBS_": ("PBS", IntegrationType.HTTP_CLIENT),
    "ETHOS_": ("Ethos", IntegrationType.SDK),
}

# JS/TS package patterns for Node.js projects
JS_PACKAGE_REGISTRY: Dict[str, tuple[str, IntegrationType]] = {
    "axios": ("Axios HTTP", IntegrationType.HTTP_CLIENT),
    "node-fetch": ("node-fetch", IntegrationType.HTTP_CLIENT),
    "got": ("Got HTTP", IntegrationType.HTTP_CLIENT),
    "@prisma/client": ("Prisma", IntegrationType.DATABASE),
    "mongoose": ("MongoDB (Mongoose)", IntegrationType.DATABASE),
    "pg": ("PostgreSQL (pg)", IntegrationType.DATABASE),
    "redis": ("Redis", IntegrationType.DATABASE),
    "ioredis": ("Redis (ioredis)", IntegrationType.DATABASE),
    "stripe": ("Stripe", IntegrationType.SDK),
    "@aws-sdk": ("AWS SDK", IntegrationType.SDK),
    "@sentry/node": ("Sentry", IntegrationType.SDK),
    "@sendgrid/mail": ("SendGrid", IntegrationType.SDK),
    "firebase-admin": ("Firebase", IntegrationType.SDK),
    "bull": ("Bull Queue", IntegrationType.MESSAGE_QUEUE),
    "bullmq": ("BullMQ", IntegrationType.MESSAGE_QUEUE),
    "amqplib": ("RabbitMQ", IntegrationType.MESSAGE_QUEUE),
    "next-auth": ("NextAuth", IntegrationType.AUTH_PROVIDER),
    "@auth/core": ("Auth.js", IntegrationType.AUTH_PROVIDER),
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "unknown"


class IntegrationDetector:
    """Detects external integrations from Python/JS source code."""

    def __init__(self) -> None:
        self._detected: Dict[str, Integration] = {}

    def detect(self, source_dir: Path) -> List[Integration]:
        """Scan source directory for integrations."""
        self._detected = {}

        if not source_dir.exists():
            return []

        # Directories to skip during scanning
        skip_dirs = {
            ".venv", "venv", "site-packages", "__pycache__", ".git", ".tox", ".mypy_cache",
            "dist", "build", ".next", "out",
        }

        # Scan Python files (skip virtualenvs and vendor dirs)
        for py_file in source_dir.rglob("*.py"):
            if skip_dirs.intersection(py_file.relative_to(source_dir).parts):
                continue
            self._scan_python_file(py_file)

        # Scan JS/TS files for env var patterns
        js_skip = skip_dirs | {"node_modules"}
        for ext in ("*.js", "*.ts", "*.jsx", "*.tsx"):
            for js_file in source_dir.rglob(ext):
                if js_skip.intersection(js_file.relative_to(source_dir).parts):
                    continue
                self._scan_js_env_vars(js_file)

        # Scan package.json for JS dependencies
        pkg_json = source_dir / "package.json"
        if pkg_json.exists():
            self._scan_package_json(pkg_json)

        return list(self._detected.values())

    def _scan_python_file(self, filepath: Path) -> None:
        """Parse a Python file's AST for imports and env var access."""
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, ValueError, OSError):
            return

        self._check_imports(tree)
        self._check_env_vars(tree, source)

    def _check_imports(self, tree: ast.AST) -> None:
        """Check import statements against the package registry."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._match_import(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._match_import(node.module)

    def _match_import(self, module_name: str) -> None:
        """Try to match an import against the registry."""
        # Try exact match first
        if module_name in PACKAGE_REGISTRY:
            name, itype = PACKAGE_REGISTRY[module_name]
            self._add_integration(name, itype, package=module_name)
            return

        # Try prefix match (e.g. 'google.cloud.storage' matches 'google.cloud')
        parts = module_name.split(".")
        for i in range(len(parts), 0, -1):
            prefix = ".".join(parts[:i])
            if prefix in PACKAGE_REGISTRY:
                name, itype = PACKAGE_REGISTRY[prefix]
                self._add_integration(name, itype, package=module_name)
                return

    def _check_env_vars(self, tree: ast.AST, source: str) -> None:
        """Detect env var access patterns like os.environ['KEY'] and os.getenv('KEY')."""
        env_vars = set()

        for node in ast.walk(tree):
            # os.environ["KEY"] or os.environ.get("KEY")
            if isinstance(node, ast.Subscript):
                if self._is_os_environ(node.value):
                    key = self._extract_string_value(node.slice)
                    if key:
                        env_vars.add(key)
            elif isinstance(node, ast.Call):
                func = node.func
                # os.environ.get("KEY")
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "get"
                    and self._is_os_environ(func.value)
                    and node.args
                ):
                    key = self._extract_string_value(node.args[0])
                    if key:
                        env_vars.add(key)
                # os.getenv("KEY")
                elif (
                    isinstance(func, ast.Attribute)
                    and func.attr == "getenv"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                    and node.args
                ):
                    key = self._extract_string_value(node.args[0])
                    if key:
                        env_vars.add(key)

        # Also detect process.env.KEY patterns in source text (for mixed codebases)
        for match in re.finditer(r"process\.env\.([A-Z_][A-Z0-9_]*)", source):
            env_vars.add(match.group(1))

        # Match env vars against patterns
        for var in env_vars:
            self._match_env_var(var)

    def _is_os_environ(self, node: ast.AST) -> bool:
        """Check if node is os.environ."""
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        )

    def _extract_string_value(self, node: ast.AST) -> Optional[str]:
        """Extract string value from an AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _match_env_var(self, var_name: str) -> None:
        """Match an env var against known patterns."""
        for pattern, (name, itype) in ENV_VAR_PATTERNS.items():
            if pattern.endswith("_"):
                if var_name.startswith(pattern) or var_name == pattern.rstrip("_"):
                    iid = _slugify(name)
                    if iid in self._detected:
                        if var_name not in self._detected[iid].env_vars:
                            self._detected[iid].env_vars.append(var_name)
                    else:
                        self._add_integration(name, itype, env_vars=[var_name])
            else:
                if var_name == pattern or var_name.startswith(pattern + "_"):
                    iid = _slugify(name)
                    if iid in self._detected:
                        if var_name not in self._detected[iid].env_vars:
                            self._detected[iid].env_vars.append(var_name)
                    else:
                        self._add_integration(name, itype, env_vars=[var_name])

    def _scan_js_env_vars(self, filepath: Path) -> None:
        """Scan JS/TS files for process.env patterns."""
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        for match in re.finditer(r"process\.env\.([A-Z_][A-Z0-9_]*)", source):
            self._match_env_var(match.group(1))

    def _scan_package_json(self, pkg_path: Path) -> None:
        """Scan package.json for known dependency packages."""
        import json

        try:
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        all_deps: Set[str] = set()
        for key in ("dependencies", "devDependencies"):
            all_deps.update((data.get(key) or {}).keys())

        for pkg, (name, itype) in JS_PACKAGE_REGISTRY.items():
            # Exact match or prefix match for scoped packages
            for dep in all_deps:
                if dep == pkg or dep.startswith(pkg + "/"):
                    self._add_integration(name, itype, package=dep)
                    break

    def _add_integration(
        self,
        name: str,
        itype: IntegrationType,
        *,
        package: Optional[str] = None,
        env_vars: Optional[List[str]] = None,
    ) -> None:
        """Add or merge an integration."""
        iid = _slugify(name)
        if iid in self._detected:
            existing = self._detected[iid]
            if package and not existing.package:
                existing.package = package
            if env_vars:
                for v in env_vars:
                    if v not in existing.env_vars:
                        existing.env_vars.append(v)
        else:
            self._detected[iid] = Integration(
                id=iid,
                name=name,
                type=itype,
                package=package,
                env_vars=env_vars or [],
            )
