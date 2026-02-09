"""Tests for JUnit XML parser."""
from pathlib import Path

from qaagent.runners.junit_parser import parse_junit_xml

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "junit"


class TestJunitParser:
    def test_parse_pytest_xml(self):
        cases = parse_junit_xml(FIXTURES / "pytest_sample.xml")
        assert len(cases) == 5

        passed = [c for c in cases if c.status == "passed"]
        failed = [c for c in cases if c.status == "failed"]
        skipped = [c for c in cases if c.status == "skipped"]

        assert len(passed) == 3
        assert len(failed) == 1
        assert len(skipped) == 1

        # Check failed case has error info
        fail = failed[0]
        assert fail.name == "test_delete_pets_pet_id_error"
        assert "500" in fail.error_message
        assert fail.output is not None

    def test_parse_playwright_xml(self):
        cases = parse_junit_xml(FIXTURES / "playwright_sample.xml")
        assert len(cases) == 3

        passed = [c for c in cases if c.status == "passed"]
        failed = [c for c in cases if c.status == "failed"]

        assert len(passed) == 2
        assert len(failed) == 1
        assert "Timeout" in failed[0].error_message

    def test_parse_behave_xml(self):
        cases = parse_junit_xml(FIXTURES / "behave_sample.xml")
        assert len(cases) == 3

        passed = [c for c in cases if c.status == "passed"]
        errors = [c for c in cases if c.status == "error"]

        assert len(passed) == 2
        assert len(errors) == 1
        assert "ConnectionRefusedError" in errors[0].error_message

    def test_parse_nonexistent_file(self):
        cases = parse_junit_xml(Path("/nonexistent/file.xml"))
        assert cases == []

    def test_parse_invalid_xml(self, tmp_path):
        bad_file = tmp_path / "bad.xml"
        bad_file.write_text("not valid xml <<>>")
        cases = parse_junit_xml(bad_file)
        assert cases == []

    def test_durations_are_floats(self):
        cases = parse_junit_xml(FIXTURES / "pytest_sample.xml")
        for c in cases:
            assert isinstance(c.duration, float)

    def test_classname_preserved(self):
        cases = parse_junit_xml(FIXTURES / "pytest_sample.xml")
        assert all(c.classname is not None for c in cases)
        assert cases[0].classname == "test_pets_api.TestPetsAPI"
