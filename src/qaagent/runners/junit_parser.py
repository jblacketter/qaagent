"""JUnit XML parser for extracting per-test results.

Handles JUnit output from pytest, Playwright, and Behave.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from qaagent.runners.base import TestCase


def parse_junit_xml(path: Path) -> List[TestCase]:
    """Parse a JUnit XML file into a list of TestCase objects.

    Handles format variations from pytest, Playwright, and Behave.
    """
    if not path.exists():
        return []

    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []

    root = tree.getroot()
    cases: List[TestCase] = []

    # Handle both <testsuites><testsuite> and bare <testsuite> roots
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        suites = [root]
    else:
        return []

    for suite in suites:
        for tc in suite.findall("testcase"):
            cases.append(_parse_testcase(tc))

    return cases


def _parse_testcase(tc: ET.Element) -> TestCase:
    """Parse a single <testcase> element."""
    name = tc.get("name", "unknown")
    classname = tc.get("classname")
    duration = float(tc.get("time", "0"))

    # Determine status from child elements
    failure = tc.find("failure")
    error = tc.find("error")
    skipped = tc.find("skipped")

    if failure is not None:
        status = "failed"
        error_message = failure.get("message", "")
        output = failure.text or ""
    elif error is not None:
        status = "error"
        error_message = error.get("message", "")
        output = error.text or ""
    elif skipped is not None:
        status = "skipped"
        error_message = skipped.get("message")
        output = None
    else:
        status = "passed"
        error_message = None
        output = None

    # Capture system-out/system-err if present
    sys_out = tc.find("system-out")
    sys_err = tc.find("system-err")
    if output is None and sys_out is not None and sys_out.text:
        output = sys_out.text
    if sys_err is not None and sys_err.text:
        extra = sys_err.text
        output = f"{output}\n{extra}" if output else extra

    return TestCase(
        name=name,
        classname=classname,
        status=status,
        duration=duration,
        output=output,
        error_message=error_message,
    )
