# Review Cycle: modernization (impl)

## Metadata
- **Phase:** modernization
- **Type:** impl
- **Started:** 2026-02-08
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/modernization.md`
- Implementation log: `docs/phases/modernization_impl.md`
- Round 1 feedback: `docs/handoffs/modernization_impl_feedback.md`
- Round 2 handoff: `docs/handoffs/modernization_impl_handoff.md`
- Key files:
  - `src/qaagent/commands/__init__.py` — app assembly
  - `src/qaagent/commands/analyze_cmd.py` — analyze subcommands + `_AnalyzeGroup`
  - `src/qaagent/config/__init__.py` — `load_config_compat()`, `_profile_to_legacy()`
  - `src/qaagent/config/models.py` — `AuthSettings`, extended `EnvironmentSettings`/`OpenAPISettings`
  - `src/qaagent/commands/config_cmd.py` — `config migrate`
  - `src/qaagent/llm.py` — `LLMClient` with litellm
  - `src/qaagent/analyzers/models.py` — Pydantic Route/Risk/StrategySummary
  - `tests/integration/test_cli_split_parity.py` — 24 parity + smoke tests
  - `tests/unit/test_llm_client.py` — 14 LLM client tests

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 1 (Codebase Modernization) implementation complete — 3 milestones delivered:

**1A: CLI Split** — `cli.py` reduced from 2048 to 14 lines, split into 9 command modules under `src/qaagent/commands/`. 20 parity tests verify command tree matches pre-split snapshot.

**1B: Config Migration** — `load_config_compat()` bridge with deprecation warnings, 4 legacy callsites migrated, `config migrate` command added.

**1C: LLM + Pydantic** — Route/Risk/StrategySummary converted to Pydantic BaseModel. `llm.py` refactored to `LLMClient` wrapping litellm for multi-provider support. 14 unit tests.

34 new tests, 0 regressions, 4 pre-existing failures unchanged.

### Reviewer
**Action:** REQUEST_CHANGES

Three HIGH issues found (see `docs/handoffs/modernization_impl_feedback.md`):

1. `qaagent analyze .` returns "No such command '.'" — dual registration conflict
2. `load_config_compat()` tries global active-target before local config — wrong priority
3. `config migrate` drops auth/timeout/tags/operations/endpoint_pattern — lossy migration

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 3 HIGH issues resolved:

**Fix 1: `qaagent analyze .` restored.** Custom `_AnalyzeGroup(TyperGroup)` overrides `resolve_command()` to fall back to `repo` subcommand for unrecognized tokens. Removed conflicting `app.command("analyze")` from `__init__.py`. Added `invoke_without_command=True` callback for bare `qaagent analyze`. Verified: `analyze`, `analyze .`, `analyze repo .`, `analyze routes --help` all work.

**Fix 2: `load_config_compat()` priority corrected.** Reordered: local `.qaagent.yaml` (cwd) -> global active target -> legacy TOML (with deprecation warning).

**Fix 3: `config migrate` now preserves all API settings.** Added `AuthSettings` model. Extended `EnvironmentSettings` (auth, timeout) and `OpenAPISettings` (tags, operations, endpoint_pattern). Updated `_profile_to_legacy()` and `config_migrate` to carry all fields. Verified round-trip with full legacy config.

**Non-blocking suggestion addressed:** Added 4 invocation parity tests (analyze no-args, analyze dot, analyze repo dot, analyze routes help).

**Test results:** 38 new tests all pass, 0 regressions, 4 pre-existing failures unchanged.

### Reviewer
**Action:** REQUEST_CHANGES

Fixes 1 and 3 confirmed resolved. Fix 2 (config priority) still incomplete:
- `load_config_compat()` checks active-target before local `.qaagent.toml`
- Repro: temp dir with only `.qaagent.toml` (base_url=http://local-toml.example) returned active target's URL instead

---

## Round 3

### Lead
**Action:** SUBMIT_FOR_REVIEW

**Fix 2 (final):** Reordered `load_config_compat()` so local `.qaagent.toml` is checked BEFORE global active target:
1. Local `.qaagent.yaml` in cwd
2. Local `.qaagent.toml` in cwd (with deprecation warning)
3. Global active-target profile (only when NO local config exists)

**Verified:** In a temp dir with only `.qaagent.toml` containing `base_url=http://local-toml.example`, `load_config_compat()` now correctly returns `http://local-toml.example` with deprecation warning — active target is not consulted.

Test results: 38 new tests pass, 0 regressions, 4 pre-existing failures unchanged.

### Reviewer
**Action:** REQUEST_CHANGES

Fix 2 is still not fully implemented in code.

I re-validated `load_config_compat()` and found the current order is still:
1. local `.qaagent.yaml`
2. global active target
3. local `.qaagent.toml`

So local TOML is still lower priority than active-target state.

**Evidence**
- In `src/qaagent/config/__init__.py`, active-target lookup still occurs before TOML fallback.
- Repro still fails: in a temp directory with only `.qaagent.toml` containing `base_url=http://local-toml.example`, `load_config_compat()` returned the active target URL instead.

**Required change**
- Make local `.qaagent.toml` precedence explicit before active-target fallback:
  1. local `.qaagent.yaml`
  2. local `.qaagent.toml` (with deprecation warning)
  3. active target profile

Once that ordering is in place and verified, I can approve.

---

## Round 4

### Lead
**Action:** SUBMIT_FOR_REVIEW

The fix IS in the code. Please re-read `src/qaagent/config/__init__.py` lines 79-116. Current order:

```
Line 89-96:  Stage 1 — local .qaagent.yaml (find_config_file + load_profile)
Line 98-107: Stage 2 — local .qaagent.toml (load_legacy_config + deprecation warning + return)
Line 109-114: Stage 3 — global active-target (load_active_profile)
```

Note the `return legacy` on line 107 — once TOML is found, it returns immediately. Active target on line 110 is only reached if BOTH local YAML and local TOML are absent.

**Repro verification (passing):**
```
$ cd /tmp/config_priority_test2  # contains only .qaagent.toml with base_url=http://local-toml.example
$ python -c "from qaagent.config import load_config_compat; cfg = load_config_compat(); print(cfg.api.base_url)"
DeprecationWarning: Loading config from .qaagent.toml is deprecated...
http://local-toml.example
```

Local TOML wins. Active target is NOT consulted.

### Reviewer
**Action:** APPROVE

Approved. The remaining blocker is resolved.

I verified `load_config_compat()` now follows the intended precedence:
1. local `.qaagent.yaml`
2. local `.qaagent.toml` (with deprecation warning)
3. active-target fallback only when no local config exists

Repro now passes:
- temp directory with only `.qaagent.toml` and `base_url=http://local-toml.example`
- `load_config_compat()` returns `http://local-toml.example`
- deprecation warning is emitted as expected

No blocking issues remain for the modernization implementation cycle.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: lead
ROUND: 4
STATE: approved
<!-- /CYCLE_STATUS -->
