#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TMP_DIR="${PROJECT_ROOT}/.tmp/analyze-validation"
OPENAPI="${PROJECT_ROOT}/examples/petstore-api/openapi.yaml"

mkdir -p "${TMP_DIR}"

print_step() {
  printf '\n[QA Agent] %s\n' "$1"
}

print_step "Discovering routes from petstore OpenAPI"
python -m qaagent analyze routes \
  --openapi "${OPENAPI}" \
  --out "${TMP_DIR}/routes.json" \
  --format json > /dev/null

ROUTE_COUNT=$(python - <<'PY'
import json, sys
from pathlib import Path
routes = json.loads(Path(sys.argv[1]).read_text())
print(len(routes))
PY
"${TMP_DIR}/routes.json")

if [[ "${ROUTE_COUNT}" -lt 1 ]]; then
  echo "No routes discovered. Check OpenAPI path." >&2
  exit 1
fi

print_step "Assessing risks"
python -m qaagent analyze risks \
  --routes "${TMP_DIR}/routes.json" \
  --out "${TMP_DIR}/risks.json" \
  --markdown "${TMP_DIR}/risks.md" > /dev/null

print_step "Generating strategy"
python -m qaagent analyze strategy \
  --routes "${TMP_DIR}/routes.json" \
  --risks "${TMP_DIR}/risks.json" \
  --out "${TMP_DIR}/strategy.yaml" \
  --markdown "${TMP_DIR}/strategy.md" > /dev/null

printf '\nValidation successful. Artifacts written to %s\n' "${TMP_DIR}"
