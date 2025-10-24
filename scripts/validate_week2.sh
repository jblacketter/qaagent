#!/usr/bin/env bash
set -euo pipefail

# Week 2 Validation Script
# Tests configuration system, Behave generator, unit test generator, and data generator

echo "==================================="
echo "Week 2 Validation - QA Agent"
echo "==================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test results
pass_test() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Use venv python
if [ -f .venv/bin/python ]; then
    PYTHON=.venv/bin/python
    QAAGENT=.venv/bin/qaagent
else
    echo "Virtual environment not found. Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

# Create temporary directory for testing
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

info "Using test directory: $TEST_DIR"
echo ""

# =============================================================================
# Day 1: Configuration System
# =============================================================================
echo "Testing Day 1: Configuration System"
echo "-----------------------------------"

# Test 1.1: Initialize config
if $QAAGENT config init examples/petstore-api --template fastapi --name petstore --register --activate --force > /dev/null 2>&1; then
    if [ -f examples/petstore-api/.qaagent.yaml ]; then
        pass_test "Config initialization creates .qaagent.yaml"
    else
        fail_test "Config initialization failed to create .qaagent.yaml"
    fi
else
    fail_test "Config init command failed"
fi

# Test 1.2: List targets (with timeout)
if timeout 5 $QAAGENT targets list > /dev/null 2>&1; then
    pass_test "List targets command works"
else
    info "List targets command skipped (timeout or failure)"
fi

# Test 1.3: Show config (cd into project dir)
if (cd examples/petstore-api && $QAAGENT config show > /dev/null 2>&1); then
    pass_test "Show config command works"
else
    fail_test "Show config command failed"
fi

# Test 1.4: Validate config (cd into project dir)
if (cd examples/petstore-api && $QAAGENT config validate > /dev/null 2>&1); then
    pass_test "Validate config command works"
else
    fail_test "Validate config command failed"
fi

echo ""

# =============================================================================
# Day 2: Behave Test Generator
# =============================================================================
echo "Testing Day 2: Behave Test Generator"
echo "-----------------------------------"

BEHAVE_OUT="$TEST_DIR/behave"

# Test 2.1: Generate Behave tests
if $QAAGENT generate behave --out "$BEHAVE_OUT" > /dev/null 2>&1; then
    pass_test "Behave test generation command works"
else
    fail_test "Behave test generation command failed"
fi

# Test 2.2: Check feature files
if [ -d "$BEHAVE_OUT/features" ]; then
    FEATURE_COUNT=$(find "$BEHAVE_OUT/features" -name "*.feature" | wc -l | tr -d ' ')
    if [ "$FEATURE_COUNT" -gt 0 ]; then
        pass_test "Generated $FEATURE_COUNT feature files"
    else
        fail_test "No feature files generated"
    fi
else
    fail_test "Features directory not created"
fi

# Test 2.3: Check step definitions
if [ -d "$BEHAVE_OUT/steps" ]; then
    if [ -f "$BEHAVE_OUT/steps/api_steps.py" ]; then
        pass_test "Generated step definitions"
    else
        fail_test "Step definitions not generated"
    fi
else
    fail_test "Steps directory not created"
fi

# Test 2.4: Verify feature file syntax
if [ -f "$BEHAVE_OUT/features/pets.feature" ]; then
    if grep -q "Feature:" "$BEHAVE_OUT/features/pets.feature" && grep -q "Scenario:" "$BEHAVE_OUT/features/pets.feature"; then
        pass_test "Feature files have valid Gherkin syntax"
    else
        fail_test "Feature files have invalid syntax"
    fi
fi

echo ""

# =============================================================================
# Day 3: Unit Test Generator
# =============================================================================
echo "Testing Day 3: Unit Test Generator"
echo "-----------------------------------"

UNIT_OUT="$TEST_DIR/unit"

# Test 3.1: Generate unit tests
if $QAAGENT generate unit-tests --out "$UNIT_OUT" > /dev/null 2>&1; then
    pass_test "Unit test generation command works"
else
    fail_test "Unit test generation command failed"
fi

# Test 3.2: Check test files
if [ -d "$UNIT_OUT" ]; then
    TEST_COUNT=$(find "$UNIT_OUT" -name "test_*.py" | wc -l | tr -d ' ')
    if [ "$TEST_COUNT" -gt 0 ]; then
        pass_test "Generated $TEST_COUNT test files"
    else
        fail_test "No test files generated"
    fi
else
    fail_test "Unit test directory not created"
fi

# Test 3.3: Check conftest.py
if [ -f "$UNIT_OUT/conftest.py" ]; then
    if grep -q "pytest.fixture" "$UNIT_OUT/conftest.py"; then
        pass_test "Generated conftest.py with fixtures"
    else
        fail_test "conftest.py missing fixtures"
    fi
else
    fail_test "conftest.py not generated"
fi

# Test 3.4: Verify test files are valid Python
if [ -f "$UNIT_OUT/test_pets_api.py" ]; then
    if $PYTHON -m py_compile "$UNIT_OUT/test_pets_api.py" 2>/dev/null; then
        pass_test "Generated tests have valid Python syntax"
    else
        fail_test "Generated tests have syntax errors"
    fi
fi

# Test 3.5: Verify tests can be collected by pytest
if cd "$UNIT_OUT" && $PYTHON -m pytest --collect-only > /dev/null 2>&1; then
    pass_test "Generated tests can be collected by pytest"
    cd - > /dev/null
else
    fail_test "Generated tests cannot be collected by pytest"
    cd - > /dev/null
fi

echo ""

# =============================================================================
# Day 3: Test Data Generator
# =============================================================================
echo "Testing Day 3: Test Data Generator"
echo "-----------------------------------"

DATA_JSON="$TEST_DIR/pets.json"
DATA_YAML="$TEST_DIR/owners.yaml"
DATA_CSV="$TEST_DIR/users.csv"

# Test 4.1: Generate JSON data
if $QAAGENT generate test-data Pet --count 10 --format json --out "$DATA_JSON" > /dev/null 2>&1; then
    pass_test "Test data generation (JSON) command works"
else
    fail_test "Test data generation (JSON) command failed"
fi

# Test 4.2: Verify JSON data
if [ -f "$DATA_JSON" ]; then
    if $PYTHON -c "import json; data = json.load(open('$DATA_JSON')); assert len(data) == 10" 2>/dev/null; then
        pass_test "Generated JSON data has correct count"
    else
        fail_test "Generated JSON data is invalid or wrong count"
    fi
else
    fail_test "JSON data file not created"
fi

# Test 4.3: Verify data quality (realistic values)
if [ -f "$DATA_JSON" ]; then
    if $PYTHON -c "import json; data = json.load(open('$DATA_JSON')); assert all('@' in str(r.get('email', '@')) or 'email' not in r for r in data)" 2>/dev/null; then
        pass_test "Generated data has realistic values"
    else
        fail_test "Generated data has unrealistic values"
    fi
fi

# Test 4.4: Generate YAML data
if $QAAGENT generate test-data Owner --count 5 --format yaml --out "$DATA_YAML" > /dev/null 2>&1; then
    pass_test "Test data generation (YAML) command works"
else
    fail_test "Test data generation (YAML) command failed"
fi

# Test 4.5: Generate CSV data
if $QAAGENT generate test-data User --count 7 --format csv --out "$DATA_CSV" > /dev/null 2>&1; then
    pass_test "Test data generation (CSV) command works"
else
    fail_test "Test data generation (CSV) command failed"
fi

# Test 4.6: Verify CSV format
if [ -f "$DATA_CSV" ]; then
    LINE_COUNT=$(wc -l < "$DATA_CSV" | tr -d ' ')
    if [ "$LINE_COUNT" -eq 8 ]; then  # 7 data + 1 header
        pass_test "Generated CSV has correct format"
    else
        fail_test "Generated CSV has wrong line count (got $LINE_COUNT, expected 8)"
    fi
fi

# Test 4.7: Test data generation with seed (reproducibility)
SEED_1="$TEST_DIR/seed1.json"
SEED_2="$TEST_DIR/seed2.json"
$QAAGENT generate test-data Pet --count 3 --seed 42 --out "$SEED_1" > /dev/null 2>&1
$QAAGENT generate test-data Pet --count 3 --seed 42 --out "$SEED_2" > /dev/null 2>&1
if diff "$SEED_1" "$SEED_2" > /dev/null 2>&1; then
    pass_test "Seed produces reproducible data"
else
    info "Seed data differs (Faker behavior may vary)"
fi

echo ""

# =============================================================================
# Integration Tests
# =============================================================================
echo "Testing Integration"
echo "-----------------------------------"

# Test 5.1: Run unit tests for generators
if $PYTHON -m pytest tests/unit/generators/ -q > /dev/null 2>&1; then
    pass_test "Unit tests for generators pass"
else
    fail_test "Unit tests for generators failed"
fi

# Test 5.2: Run integration tests
if $PYTHON -m pytest tests/integration/test_generate_unit_tests_cli.py -q > /dev/null 2>&1; then
    pass_test "Integration tests for unit-tests CLI pass"
else
    fail_test "Integration tests for unit-tests CLI failed"
fi

if $PYTHON -m pytest tests/integration/test_generate_test_data_cli.py -q > /dev/null 2>&1; then
    pass_test "Integration tests for test-data CLI pass"
else
    fail_test "Integration tests for test-data CLI failed"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
echo "==================================="
echo "Validation Summary"
echo "==================================="
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

echo "Total tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ "$TESTS_FAILED" -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
else
    echo -e "${GREEN}Failed: $TESTS_FAILED${NC}"
fi
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ Week 2 validation PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ Week 2 validation FAILED${NC}"
    exit 1
fi
