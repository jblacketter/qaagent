# Review Cycle: phase7 (plan)

## Metadata
- **Phase:** phase7
- **Type:** plan
- **Started:** 2026-02-14
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/phase7.md`
- Decision Log: `docs/decision_log.md`
- Roadmap: `docs/ROADMAP.md`

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 7 plan covers adding custom risk rules via YAML to the existing pluggable rule engine (16 built-in Python rules from Phase 4). Organized into 3 priorities:

- **P1 (Core Engine):** `YamlRiskRule` class extending `RiskRule`, Pydantic schema models for YAML parsing (`CustomRuleDefinition`, `PathCondition`, `MatchCondition`, etc.), unit tests for all condition types.
- **P2 (Config Integration):** Add `custom_rules` and `custom_rules_file` fields to `RiskAssessmentSettings`, update `default_registry()` to load YAML rules, thread custom rules through `assess_risks()` and its CLI callers.
- **P3 (CLI Commands):** New `qaagent rules` subcommand group (`list`, `validate`, `show`), integration tests via CliRunner.

Key design decisions:
1. **AND-only logic** between match conditions — no OR operator (keeps schema predictable).
2. **Per-route rules only** — aggregate rules (`evaluate_all`) stay Python-only.
3. **Minimal condition set**: path/method/auth_required/tags/deprecated. Parameter and response conditions deferred.
4. **Severity override**: YAML rule with same `rule_id` as built-in replaces it in registry (enables severity downgrades without disabling).
5. **Severity escalation**: Ordered list of condition→severity pairs; first match wins.

8 new files to create (~1,035 lines total), 7 existing files modified (~49 lines added). No breaking changes to existing RiskRule/RiskRuleRegistry API.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

Plan quality is high overall, but there are 2 blocking design gaps that need to be resolved before implementation:

1. **[P1] Built-in severity override semantics are contradictory and currently not implementable as written.**
   - `docs/phases/phase7.md:80`-`docs/phases/phase7.md:87` documents an override like:
     - `rule_id: SEC-001`
     - `severity: medium`
     - with inherited built-in matching/metadata.
   - But `docs/phases/phase7.md:103`-`docs/phases/phase7.md:106` says same-ID YAML rules replace built-ins in the registry.
   - In current code, built-in behavior lives inside each rule class’s `evaluate()` logic (for example `src/qaagent/analyzers/rules/security.py:17`), so replacement with a generic YAML per-route rule does not automatically preserve built-in matching and aggregate behavior.
   - Please explicitly define one mechanism and data model for overrides:
     - either a dedicated built-in severity override map (recommended), or
     - a wrapper/decorator strategy for existing rules,
     - and clarify whether aggregate rules (`REL-003`, `REL-004`) are overrideable or excluded.

2. **[P2] `custom_rules_file` path resolution is underspecified (likely CWD-dependent bug).**
   - Plan adds `custom_rules_file` to `RiskAssessmentSettings` (`docs/phases/phase7.md:26`, `docs/phases/phase7.md:134`) but does not define how relative paths are resolved.
   - Existing config already has explicit project-root resolution for spec files (`src/qaagent/config/models.py:128`), and active targets are often run from outside repo root.
   - Please add explicit resolution semantics and implementation location (for example a `resolve_custom_rules_path(project_root)` helper on profile/settings) plus tests for relative and absolute paths.

Once these two items are clarified in the plan, I can re-review quickly.

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

Both blocking issues resolved in `docs/phases/phase7.md`:

**1. Severity override semantics (was contradictory) → now a dedicated override map.**

Severity overrides are fully separated from custom rules. New config field:
```yaml
risk_assessment:
  severity_overrides:
    "SEC-001": medium
    "PERF-001": low
```

Mechanism: `RiskRuleRegistry.run_all()` applies overrides as a post-processing step — after each rule's `evaluate()`/`evaluate_all()` produces `Risk` objects, matching entries in `severity_overrides` remap `risk.severity`. This preserves all built-in logic (matching, metadata, aggregate behavior for REL-003/REL-004). Custom YAML rules must use unique `rule_id` values; `qaagent rules validate` rejects collisions with built-in IDs.

Removed the old "same rule_id replaces built-in" design entirely.

**2. `custom_rules_file` path resolution (was underspecified) → explicit project-root resolution.**

Added `resolve_custom_rules_path(project_root: Path) -> Optional[Path]` on `QAAgentProfile`, following the exact same pattern as `resolve_spec_path()` (`src/qaagent/config/models.py:126-132`): relative paths resolve against project root, absolute paths pass through. `_resolve_risk_config()` receives `project_root` from the active target or `Path.cwd()`. Tests cover relative path, absolute path, and missing file cases.

Updated success criteria to include: severity_overrides for aggregate rules, custom rule ID collision rejection, and path resolution verification.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

Round 1 blockers were addressed, but 2 additional blocking gaps remain:

1. **[P1] Rule-ID collision protection is only defined for `qaagent rules validate`, not for runtime risk execution.**
   - Plan currently states collision rejection in validator flow (`docs/phases/phase7.md:104`, `docs/phases/phase7.md:167`), but `assess_risks()`/`default_registry()` also load rules directly.
   - Current registry semantics overwrite on duplicate IDs (`src/qaagent/analyzers/rules/base.py:47`), so a colliding custom rule could still replace a built-in if users skip `rules validate`.
   - Please require collision rejection in the runtime load path as well (loader and/or registry wiring), and add tests that call `assess_risks()` directly to prove built-ins cannot be replaced by collision.

2. **[P2] Merge/precedence semantics for inline `custom_rules` + `custom_rules_file` are unspecified.**
   - New threading returns both inline rules and a file path (`docs/phases/phase7.md:135`, `docs/phases/phase7.md:138`) but does not define merge order, duplicate handling, or conflict behavior.
   - Please specify deterministic behavior (for example, file-first then inline overrides, or hard-error on duplicate `rule_id` across sources) and include explicit tests.

Once these are defined in the plan, I can re-review quickly.

---

## Round 3

### Lead
**Action:** SUBMIT_FOR_REVIEW

Both Round 2 blockers resolved in `docs/phases/phase7.md`:

**1. Rule-ID collision protection at runtime (was CLI-only) → enforced in loader.**

`load_rules_from_dicts()` and `load_rules_from_yaml()` now accept a `builtin_ids: Set[str]` parameter. If any custom rule's `rule_id` collides with a built-in ID, the loader raises `ValueError` — this happens on every code path including `assess_risks()` and `default_registry()`, not just `qaagent rules validate`. Added success criteria: "Calling `assess_risks()` directly with a colliding custom rule raises `ValueError`."

**2. Merge/precedence for inline + file rules (was unspecified) → deterministic with hard error on duplicates.**

Merge order: file rules load first, inline rules load second. Duplicate `rule_id` across sources is a hard `ValueError` — no silent override, no precedence ambiguity. Tests cover: file-only, inline-only, file+inline with unique IDs (merged), file+inline with duplicate ID (error).

New section "Merge Precedence: Inline `custom_rules` + `custom_rules_file`" added to Architecture with error message format example.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

Round 3 resolves both remaining blockers from my previous review:

1. Runtime collision handling is now explicitly defined at loader/runtime level (not validator-only), with `ValueError` on built-in/custom `rule_id` collisions across all paths including direct `assess_risks()` usage.
2. Inline + file rule merge behavior is now deterministic and testable (file first, inline second, hard error on duplicate `rule_id` across sources).

No new blocking issues found in the revised plan.

Next step: proceed to implementation kickoff for Phase 7.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 3
STATE: approved
<!-- /CYCLE_STATUS -->
