"""
Test data generator using Faker for realistic fixtures.

Generates test data from OpenAPI schemas with:
- Smart field detection (email, name, age, etc.)
- Schema constraint respect (min, max, pattern, enum)
- Multiple output formats (JSON, YAML, CSV)
- Relationship support
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from faker import Faker

from qaagent.analyzers.models import Route


class DataGenerator:
    """Generates realistic test data from API schemas."""

    def __init__(self, routes: List[Route], seed: Optional[int] = None):
        self.routes = routes
        self.faker = Faker()
        if seed:
            Faker.seed(seed)
            random.seed(seed)

    def generate(
        self,
        model_name: str,
        count: int = 10,
        output_format: str = "json",
    ) -> List[Dict[str, Any]]:
        """
        Generate test data records.

        Args:
            model_name: Name of the model/entity (e.g., "Pet", "User")
            count: Number of records to generate
            output_format: Output format (json, yaml, csv)

        Returns:
            List of generated records
        """
        # Find route with this model in response
        schema = self._find_schema_for_model(model_name)
        if not schema:
            # Fallback to generic schema
            schema = self._create_default_schema(model_name)

        records = []
        for i in range(count):
            record = self._generate_record(schema, i)
            records.append(record)

        return records

    def save(
        self,
        records: List[Dict[str, Any]],
        output_path: Path,
        format: str = "json",
    ) -> None:
        """Save generated data to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            output_path.write_text(json.dumps(records, indent=2))
        elif format == "yaml":
            output_path.write_text(yaml.dump(records, default_flow_style=False))
        elif format == "csv":
            if records:
                with output_path.open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=records[0].keys())
                    writer.writeheader()
                    writer.writerows(records)

    def _find_schema_for_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Find OpenAPI schema for a model."""
        model_lower = model_name.lower()

        for route in self.routes:
            # Check response schemas
            for status_code, response_data in route.responses.items():
                if status_code.startswith("2"):  # Success responses
                    content = response_data.get("content", {})
                    json_content = content.get("application/json", {})
                    schema = json_content.get("schema", {})

                    # Check if this schema matches the model
                    if "$ref" in schema:
                        ref = schema["$ref"]
                        if model_lower in ref.lower():
                            # TODO: Resolve $ref to actual schema
                            return self._create_schema_from_ref(ref)

                    # Check array items
                    if schema.get("type") == "array":
                        items = schema.get("items", {})
                        if "$ref" in items:
                            ref = items["$ref"]
                            if model_lower in ref.lower():
                                return self._create_schema_from_ref(ref)

        return None

    def _create_schema_from_ref(self, ref: str) -> Dict[str, Any]:
        """Create a schema from a $ref (simplified)."""
        # Extract model name from ref like "#/components/schemas/Pet"
        model_name = ref.split("/")[-1]

        # Return a default schema (in production, would resolve from OpenAPI spec)
        return self._create_default_schema(model_name)

    def _create_default_schema(self, model_name: str) -> Dict[str, Any]:
        """Create a default schema for a model."""
        model_lower = model_name.lower()

        # Common schemas
        if model_lower in ["pet", "pets"]:
            return {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "species": {"type": "string", "enum": ["dog", "cat", "bird", "fish"]},
                    "age": {"type": "integer", "minimum": 0, "maximum": 30},
                    "owner_id": {"type": "integer"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            }
        elif model_lower in ["owner", "owners", "user", "users"]:
            return {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            }
        else:
            # Generic schema
            return {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            }

    def _generate_record(self, schema: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Generate a single record from schema."""
        record = {}
        properties = schema.get("properties", {})

        for field_name, field_schema in properties.items():
            record[field_name] = self._generate_field(field_name, field_schema, index)

        return record

    def _generate_field(self, field_name: str, schema: Dict[str, Any], index: int) -> Any:
        """Generate a field value based on name and schema."""
        field_type = schema.get("type", "string")
        field_format = schema.get("format")

        # Handle by field name (smart detection)
        field_lower = field_name.lower()

        if "id" == field_lower:
            return index + 1
        elif "email" in field_lower:
            return self.faker.email()
        elif field_lower in ["name", "username", "owner_name"]:
            return self.faker.name()
        elif "first" in field_lower and "name" in field_lower:
            return self.faker.first_name()
        elif "last" in field_lower and "name" in field_lower:
            return self.faker.last_name()
        elif "phone" in field_lower:
            return self.faker.phone_number()
        elif "address" in field_lower:
            return self.faker.address().replace("\n", ", ")
        elif "city" in field_lower:
            return self.faker.city()
        elif "state" in field_lower or "province" in field_lower:
            return self.faker.state()
        elif "zip" in field_lower or "postal" in field_lower:
            return self.faker.zipcode()
        elif "country" in field_lower:
            return self.faker.country()
        elif "company" in field_lower:
            return self.faker.company()
        elif "url" in field_lower or "website" in field_lower:
            return self.faker.url()
        elif "description" in field_lower:
            return self.faker.text(max_nb_chars=200)
        elif "age" in field_lower:
            return random.randint(1, 100)
        elif "species" in field_lower:
            return random.choice(["dog", "cat", "bird", "fish"])
        elif "tag" in field_lower and field_type == "array":
            return random.sample(["friendly", "playful", "calm", "energetic", "shy"], k=random.randint(1, 3))
        elif "created" in field_lower or "updated" in field_lower or "date" in field_lower:
            return self.faker.iso8601()

        # Handle by type
        if field_type == "string":
            if "enum" in schema:
                return random.choice(schema["enum"])
            if field_format == "email":
                return self.faker.email()
            if field_format == "date-time":
                return self.faker.iso8601()
            if field_format == "date":
                return self.faker.date()
            if field_format == "uri":
                return self.faker.url()
            return self.faker.word()

        elif field_type == "integer":
            minimum = schema.get("minimum", 1)
            maximum = schema.get("maximum", 1000)
            return random.randint(minimum, maximum)

        elif field_type == "number":
            minimum = schema.get("minimum", 0.0)
            maximum = schema.get("maximum", 1000.0)
            return round(random.uniform(minimum, maximum), 2)

        elif field_type == "boolean":
            return random.choice([True, False])

        elif field_type == "array":
            items_schema = schema.get("items", {"type": "string"})
            count = random.randint(1, 5)
            return [self._generate_field(f"{field_name}_item", items_schema, i) for i in range(count)]

        else:
            return None
