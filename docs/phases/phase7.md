# Phase: Custom Risk Rules via YAML

## Status
- [x] Planning
- [x] In Review
- [x] Approved
- [x] Implementation
- [x] Implementation Review
- [x] Complete

## Roles
- Lead: claude
- Reviewer: codex
- Arbiter: Human

## Summary
**What:** Allow users to define custom per-route risk rules in YAML (inline in `.qaagent.yaml` or a separate file), extending the existing pluggable rule engine without writing Python.
**Why:** The Phase 4 rule engine ships 16 hardcoded rules. Users need to add project-specific rules (e.g., "flag GraphQL introspection endpoints", "require auth on /internal/* paths") but currently must write Python classes. A YAML DSL makes the rule engine accessible to non-developers and enables version-controlled, per-project customization.
**Depends on:** Phase 4 (Enhanced Analysis) — Complete

## Scope

### In Scope
- YAML schema for per-route risk rule definitions (match conditions + risk metadata)
- `YamlRiskRule` class implementing `RiskRule.evaluate()` from parsed YAML conditions
- Loading custom rules from `.qaagent.yaml` (inline `custom_rules` list) or separate file (`custom_rules_file`)
- Severity override for built-in rules via a dedicated `severity_overrides` map (does not replace the built-in rule's logic)
- Severity escalation within a rule (e.g., medium normally → critical if path contains "admin")
- Match condition operators: path (equals/contains/regex/starts_with/not_contains), method (equals/in), auth_required (equals), tags (contains/empty), deprecated (equals)
- CLI subcommand group: `qaagent rules list`, `qaagent rules validate [file]`, `qaagent rules show <rule-id>`
- Unit and integration tests for all new code
- Test fixture YAML files (valid + invalid)

### Out of Scope
- Aggregate rules (`evaluate_all`) — too complex for declarative YAML; keep Python-only
- OR logic between conditions — AND-only keeps the schema simple and predictable
- Parameter-level conditions (checking specific param names/schemas) — complex nested structure, can be added later
- Response-level conditions (checking response status codes/schemas) — same reason
- Documentation guide (`docs/guides/custom_risk_rules.md`) — follow-up task
- Dashboard/API integration for custom rules — follow-up task

## Technical Approach

### YAML Schema

**Inline in `.qaagent.yaml`:**
```yaml
risk_assessment:
  disable_rules: ["SEC-002"]
  custom_rules:
    - rule_id: "CUSTOM-001"
      category: security
      severity: high
      title: "GraphQL introspection enabled"
      description: "GraphQL introspection should be disabled in production"
      recommendation: "Disable introspection in production config"
      match:
        path: { contains: "/graphql" }
        method: { in: ["POST", "GET"] }
      cwe_id: "CWE-200"
```

**Separate file (`risk_rules.yaml`):**
```yaml
rules:
  - rule_id: "CUSTOM-002"
    category: performance
    severity: medium
    title: "Unbounded export endpoint"
    description: "Export endpoints without pagination may cause OOM"
    recommendation: "Add limit/offset or streaming"
    match:
      path: { regex: ".*/export$" }
      method: { equals: "GET" }
    severity_escalation:
      - condition: { path: { contains: "admin" } }
        severity: critical
```

**Severity override for built-in rules** (separate from custom rules — does not replace the rule):
```yaml
risk_assessment:
  severity_overrides:
    "SEC-001": medium     # Downgrade from HIGH to MEDIUM
    "PERF-001": low       # Downgrade pagination warning
```

This uses the existing `severity_thresholds` field location in `RiskAssessmentSettings` (renamed to `severity_overrides` for clarity). Overrides apply as a post-processing step after `evaluate()` returns a `Risk` — the built-in rule's matching logic and metadata are fully preserved; only `risk.severity` is remapped. Aggregate rules (`REL-003`, `REL-004`) are also overrideable since the override operates on the output `Risk`, not the rule class.

### Match Condition Operators

All conditions within `match` use AND logic. Each field supports these operators:

| Field | Operators | Example |
|-------|-----------|---------|
| `path` | `equals`, `contains`, `regex`, `starts_with`, `not_contains` (list) | `path: { regex: "^/api/v\\d+/" }` |
| `method` | `equals`, `in` (list) | `method: { in: ["POST", "PUT"] }` |
| `auth_required` | `equals` (bool) | `auth_required: { equals: false }` |
| `tags` | `contains` (str), `empty` (bool) | `tags: { empty: true }` |
| `deprecated` | `equals` (bool) | `deprecated: { equals: true }` |

### Architecture

**Custom YAML rules** (`YamlRiskRule`) extend the existing `RiskRule` ABC. Each is constructed from a `CustomRuleDefinition` Pydantic model. The `evaluate()` method checks all match conditions against a `Route` and returns a `Risk` if all conditions match. Severity escalation rules are checked in order; first match wins. Custom rules must use unique `rule_id` values (conventionally `CUSTOM-XXX`).

**Rule-ID collision protection** is enforced at the loader level, not just in the CLI validator. `load_rules_from_dicts()` and `load_rules_from_yaml()` both accept a `builtin_ids: Set[str]` parameter (the set of all built-in rule IDs from `default_registry()`). If any custom rule's `rule_id` matches a built-in ID, the loader raises a `ValueError` with a clear message naming the collision. This means collision rejection happens on every code path — `assess_risks()`, `qaagent rules validate`, and any future caller. Tests verify that calling `assess_risks()` directly with a colliding custom rule raises `ValueError` and does not silently replace the built-in.

**Severity overrides** are a separate mechanism from custom rules. They are a simple `Dict[str, str]` mapping `rule_id → severity` in config. Overrides are applied as a post-processing step in `RiskRuleRegistry.run_all()`: after each rule's `evaluate()`/`evaluate_all()` produces `Risk` objects, any matching `severity_overrides` entry remaps the `risk.severity` field. This preserves the built-in rule's matching logic, metadata, and aggregate behavior (e.g., `REL-003` and `REL-004` remain fully functional). The override map works for both built-in and custom rule IDs.

Custom YAML rules register into the same `RiskRuleRegistry` alongside built-in Python rules. The `default_registry()` function gains optional parameters for custom rules and severity overrides, threaded through from the profile config.

### Merge Precedence: Inline `custom_rules` + `custom_rules_file`

When both `custom_rules` (inline) and `custom_rules_file` are specified, the merge order is:

1. **File rules load first** — `custom_rules_file` is parsed into `List[CustomRuleDefinition]`
2. **Inline rules load second** — `custom_rules` from `.qaagent.yaml` are appended
3. **Duplicate `rule_id` across sources is a hard error** — if the same `rule_id` appears in both the file and inline config, the loader raises `ValueError` naming the duplicate and both sources

This is deterministic and fail-fast. Users who want to split rules between file and inline must use distinct IDs. The error message format:

```
Duplicate rule_id 'CUSTOM-003' found in both custom_rules_file ('risk_rules.yaml') and inline custom_rules. Use unique rule_id values across all sources.
```

Tests cover: file-only, inline-only, file+inline with unique IDs (merged correctly), file+inline with duplicate ID (ValueError raised).

### Path Resolution for `custom_rules_file`

Relative paths in `custom_rules_file` are resolved against the project root (the directory containing `.qaagent.yaml`), following the same pattern as `resolve_spec_path()` in `QAAgentProfile` (`src/qaagent/config/models.py:126-132`). A new method `resolve_custom_rules_path(project_root: Path) -> Optional[Path]` is added to `RiskAssessmentSettings` (or `QAAgentProfile`) using the same logic:

```python
def resolve_custom_rules_path(self, project_root: Path) -> Optional[Path]:
    if not self.risk_assessment.custom_rules_file:
        return None
    candidate = Path(self.risk_assessment.custom_rules_file)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate
```

Tests cover: relative path resolution, absolute path passthrough, missing file returns `None` or raises clear error.

### Config Threading

Current flow:
```
CLI command → load_active_profile() → _resolve_disabled_rules(profile) → assess_risks(routes, disabled_rules)
```

New flow:
```
CLI command → load_active_profile() → _resolve_risk_config(profile, project_root) → assess_risks(routes, disabled_rules, custom_rules, custom_rules_path, severity_overrides)
```

The helper `_resolve_disabled_rules()` in `commands/generate_cmd.py` is extended to `_resolve_risk_config()` returning disabled rules, inline custom rules, resolved custom rules file path, and severity overrides. `project_root` comes from the active target or `Path.cwd()`.

## Files to Create/Modify

### New Files
- `src/qaagent/analyzers/rules/yaml_loader.py` (~150 lines) — Pydantic models + YAML parsing
- `src/qaagent/analyzers/rules/yaml_rule.py` (~120 lines) — YamlRiskRule implementation
- `src/qaagent/commands/rules_cmd.py` (~120 lines) — CLI subcommands
- `tests/unit/analyzers/test_yaml_rules.py` (~300 lines) — Rule evaluation tests
- `tests/unit/analyzers/test_yaml_loader.py` (~150 lines) — Schema/loading tests
- `tests/integration/commands/test_rules_cmd.py` (~150 lines) — CLI tests
- `tests/fixtures/data/custom_rules_valid.yaml` (~30 lines) — Valid fixture
- `tests/fixtures/data/custom_rules_invalid.yaml` (~15 lines) — Invalid fixture

### Modified Files
- `src/qaagent/config/models.py` (+15 lines) — Add `custom_rules`, `custom_rules_file`, `severity_overrides` to `RiskAssessmentSettings`; add `resolve_custom_rules_path()` to `QAAgentProfile`
- `src/qaagent/analyzers/rules/__init__.py` (+20 lines) — Update `default_registry()` to load YAML rules
- `src/qaagent/analyzers/risk_assessment.py` (+10 lines) — Thread custom_rules through `assess_risks()`
- `src/qaagent/commands/analyze_cmd.py` (+5 lines) — Pass custom rules from profile
- `src/qaagent/commands/generate_cmd.py` (+5 lines) — Pass custom rules from profile
- `src/qaagent/commands/__init__.py` (+3 lines) — Register `rules_app`
- `tests/fixtures/cli_snapshots/pre_split_commands.json` (+1 entry) — Add `rules` subcommand

## Success Criteria
- [x] Users can define custom rules in `.qaagent.yaml` inline or via separate file
- [x] Match conditions work: path (equals/contains/regex/starts_with/not_contains), method (equals/in), auth_required (equals), tags (contains/empty), deprecated (equals)
- [x] Severity escalation applies correctly (first matching escalation wins)
- [x] `severity_overrides` map remaps built-in rule severity without replacing rule logic
- [x] `severity_overrides` works for aggregate rules (REL-003, REL-004)
- [x] Custom rules with built-in `rule_id` are rejected at load time (ValueError), not just in `qaagent rules validate`
- [x] Calling `assess_risks()` directly with a colliding custom rule raises `ValueError`
- [x] File + inline custom rules merge deterministically (file first, inline second)
- [x] Duplicate `rule_id` across file and inline sources raises `ValueError`
- [x] `custom_rules_file` relative paths resolve against project root (matching `resolve_spec_path` pattern)
- [x] `qaagent rules list` shows both built-in and custom rules
- [x] `qaagent rules validate` reports schema errors with clear messages
- [x] `qaagent rules show <id>` displays full rule details
- [x] `disable_rules` works for both built-in and custom rules
- [x] All existing tests pass (no regressions)
- [x] New tests cover happy path + error cases for all condition types

## Open Questions
- None — scope is well-defined by existing rule engine architecture.

## Risks
- **Regex DoS**: User-supplied regex in YAML conditions could hang evaluation on pathological input. Mitigation: compile regex at load time with `re.compile()`, catch `re.error` and report clearly; route paths are short strings so evaluation is bounded.
- **Schema complexity**: Too many condition operators could overwhelm users. Mitigation: ship the minimal set above (path/method/auth/tags/deprecated); param/response conditions deferred to follow-up.
- **Config threading**: `assess_risks()` callers need to pass custom rules from profile. Mitigation: small, mechanical change — extend existing `_resolve_disabled_rules` helper to also return custom rules config.
- **Rule ID conflicts**: Users might accidentally use a built-in rule_id. Mitigation: loader raises `ValueError` on collision at every code path (not just CLI validate); document namespace convention (use `CUSTOM-` prefix).
