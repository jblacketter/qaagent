# Phase: Codebase Modernization

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
**What:** Modernize the codebase to eliminate technical debt, unify patterns, and prepare for the Test Framework Generation Engine (Phase 2).
**Why:** The current codebase has grown organically over 3 sprints. Key friction points (monolithic CLI, dual config, Ollama-only LLM) will slow Phase 2 development and make the project harder to maintain.
**Depends on:** None

## Milestones

Phase 1 is split into 3 shippable milestones. Each milestone is independently valuable and testable.

### Milestone 1A: CLI Split
Split `cli.py` into command modules. No behavior changes.

### Milestone 1B: Config Migration
Staged removal of legacy config with compatibility shim.

### Milestone 1C: LLM + Pydantic
Multi-provider LLM via litellm, Pydantic model standardization.

---

## Scope

### In Scope
1. **Split cli.py into command modules** - Move each subcommand group into `src/qaagent/commands/`
2. **Staged legacy config removal** - Compatibility shim → deprecation warnings → migration utility → removal
3. **Multi-provider LLM module via litellm** - Wrap litellm for Anthropic/OpenAI/Ollama with thin client boundary
4. **Standardize data models** - Convert analyzer dataclasses to Pydantic models
5. **Update pyproject.toml** - Update `[llm]` extras, add `ruff` to dev deps

### Out of Scope
- New features (test generation improvements, new route discovery)
- Dashboard redesign
- CI/CD pipeline changes
- Documentation overhaul

---

## Technical Approach

### 1. CLI Split (Milestone 1A)

Current `cli.py` (2048 lines) -> split into:
```
src/qaagent/commands/
├── __init__.py          (app assembly: import and register all subcommands)
├── analyze.py           (existing, add analyze subcommands from cli.py)
├── config_cmd.py        (config init/validate/show)
├── targets_cmd.py       (targets add/list/remove, use)
├── generate_cmd.py      (generate behave/unit-tests/test-data/openapi)
├── workspace_cmd.py     (workspace show/list/clean/apply)
├── run_cmd.py           (pytest-run, schemathesis-run, playwright-*, a11y, lighthouse, perf)
├── report_cmd.py        (report, dashboard)
└── misc_cmd.py          (doctor, version, web-ui, api, fix)
```
The main `cli.py` becomes a thin assembly file (~50 lines) that imports and registers subcommands.

**Shared helpers**: `_load_json_or_yaml()`, `_load_routes_from_file()`, `_load_risks_from_file()`, `_print_routes_table()`, `_target_manager()`, `_resolve_project_path()` move to `src/qaagent/commands/_helpers.py`.

#### Command-Parity Verification

Automated verification added as a success criterion:

1. **Help tree parity test** (`tests/integration/test_cli_split_parity.py`):
   - Capture `qaagent --help` output before and after split
   - Assert identical command names, subcommand names, and option signatures
   - Run via `typer.testing.CliRunner`

2. **Option parity for critical commands**:
   - For each of `analyze routes`, `generate behave`, `schemathesis-run`, `config init`:
     - Assert `--help` output matches pre-split snapshot

3. **Smoke tests per command group**:
   - `analyze routes --help` exits 0
   - `generate behave --help` exits 0
   - `config show --help` exits 0
   - `doctor --json` exits 0 or 1 (not 2)
   - `targets list` exits 0

### 2. Config Migration (Milestone 1B)

Staged migration path for legacy config removal:

#### Stage 1: Compatibility Bridge
- Create `load_config_compat()` in `config/__init__.py` that:
  1. First tries `load_active_profile()` (new YAML system)
  2. Falls back to `load_config()` (legacy TOML) if no YAML config found
  3. When falling back, emits a deprecation warning via `warnings.warn()`
- Replace all 4 callsites (`cli.py:1218`, `cli.py:1912`, `cli.py:1992`, `mcp_server.py:137`) with `load_config_compat()`

#### Stage 2: Migration Utility
- Add `qaagent config migrate` command that:
  1. Reads `.qaagent.toml` (legacy)
  2. Converts to `.qaagent.yaml` format (new `QAAgentProfile`)
  3. Writes `.qaagent.yaml` alongside the TOML
  4. Prints diff and instructions

#### Stage 3: Removal (end of Phase 1)
- Delete `config/legacy.py`
- Remove `load_config_compat()` fallback
- Remove `QAAgentConfig` alias from `config/__init__.py`
- Only proceed once migration utility has been available for the full phase

**Callers to migrate (4 total):**
| File | Line | Current Call | What it reads |
|------|------|-------------|---------------|
| `cli.py` | 1218 | `load_config()` | API openapi, base_url, auth for schemathesis-run |
| `cli.py` | 1912 | `load_config()` | API config for gen-tests |
| `cli.py` | 1992 | `load_config()` | API config for summarize |
| `mcp_server.py` | 137 | `load_config()` | API config for schemathesis_run tool |

### 3. LLM Multi-Provider via litellm (Milestone 1C)

Codex recommended litellm-first. Agreed - `litellm` is already in `pyproject.toml [llm]` extras and handles retry, rate-limiting, and error normalization out of the box.

Refactor `llm.py` to:
```python
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str

class ChatResponse(BaseModel):
    content: str
    model: str
    usage: dict | None = None

class LLMClient:
    """Thin wrapper around litellm with qaagent defaults."""

    def __init__(self, config: LLMSettings | None = None):
        self.config = config or _load_llm_settings()

    def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send messages to configured LLM provider via litellm."""
        ...

    def available(self) -> bool:
        """Check if the configured provider is reachable."""
        ...
```

**Wrapper boundaries:**
- `LLMClient` is the ONLY place that imports `litellm`
- All qaagent code calls `LLMClient`, never litellm directly
- `LLMClient.chat()` accepts and returns typed Pydantic models (not raw dicts)
- Provider selection: `LLMSettings.provider` maps to litellm model string format (e.g., `"anthropic/claude-sonnet-4-5-20250929"`, `"ollama/qwen2.5:7b"`, `"gpt-4o"`)
- Retry/rate-limit: delegated to litellm's built-in mechanisms
- Error normalization: litellm raises typed exceptions; `LLMClient` wraps them in `QAAgentLLMError`

**Config resolution order:**
1. `LLMSettings` from `.qaagent.yaml` profile
2. `QAAGENT_LLM` / `QAAGENT_MODEL` env vars
3. Defaults: `provider="ollama"`, `model="qwen2.5:7b"`

### 4. Pydantic Standardization (Milestone 1C)

Convert `Route`, `Risk`, `StrategySummary` from `@dataclass` to `pydantic.BaseModel`:
- Replace `to_dict()` with `.model_dump()`
- Replace `from_dict()` with `.model_validate()`
- Enables JSON schema generation for MCP tool descriptions
- All return types from generators/analyzers become Pydantic models
- **Typed return models for future LLMTestGenerator**: `GeneratedTest(BaseModel)`, `GeneratedAssertion(BaseModel)`, etc. (defined now, used in Phase 2)

---

## Files to Create/Modify

### Milestone 1A (CLI Split)
- `src/qaagent/commands/__init__.py` - rewrite as app assembly
- `src/qaagent/commands/_helpers.py` - new (shared CLI utilities)
- `src/qaagent/commands/config_cmd.py` - new
- `src/qaagent/commands/targets_cmd.py` - new
- `src/qaagent/commands/generate_cmd.py` - new
- `src/qaagent/commands/workspace_cmd.py` - new
- `src/qaagent/commands/run_cmd.py` - new
- `src/qaagent/commands/report_cmd.py` - new
- `src/qaagent/commands/misc_cmd.py` - new
- `src/qaagent/cli.py` - rewrite to thin assembly (~50 lines)
- `tests/integration/test_cli_split_parity.py` - new (parity verification)

### Milestone 1B (Config Migration)
- `src/qaagent/config/__init__.py` - add `load_config_compat()`, deprecation warnings
- `src/qaagent/commands/config_cmd.py` - add `migrate` subcommand
- `src/qaagent/config/legacy.py` - delete (after migration utility ships)

### Milestone 1C (LLM + Pydantic)
- `src/qaagent/llm.py` - refactor to litellm-backed `LLMClient` with Pydantic types
- `src/qaagent/analyzers/models.py` - convert to Pydantic BaseModel
- `pyproject.toml` - update `[llm]` extras
- `tests/unit/test_llm_client.py` - new (mock litellm tests)

---

## Success Criteria

### Milestone 1A
- [ ] `cli.py` is under 100 lines
- [ ] `qaagent --help` output identical before and after split
- [ ] Help tree parity test passes (automated)
- [ ] Option parity for `analyze routes`, `generate behave`, `schemathesis-run`, `config init`
- [ ] Smoke test exits 0 for each command group (`--help`)
- [ ] All existing tests pass

### Milestone 1B
- [ ] `load_config_compat()` falls back to legacy with deprecation warning
- [ ] `qaagent config migrate` converts `.qaagent.toml` → `.qaagent.yaml`
- [ ] After migration, all 4 legacy callsites work via new profile loader
- [ ] `config/legacy.py` deleted, no code references `LegacyQAAgentConfig`

### Milestone 1C
- [ ] `QAAGENT_LLM=anthropic` with `ANTHROPIC_API_KEY` set → `LLMClient.chat()` works
- [ ] `QAAGENT_LLM=ollama` still works as before
- [ ] `LLMClient.chat()` returns typed `ChatResponse` (not raw dict)
- [ ] `Route`, `Risk`, `StrategySummary` are Pydantic BaseModel subclasses
- [ ] `.model_dump()` and `.model_validate()` work for all models
- [ ] All existing tests pass, no regressions

---

## Risks
- **CLI behavior regression**: Mitigate with automated help-tree parity test and per-group smoke tests
- **Config migration breaks existing setups**: Mitigate with staged removal (shim → warning → utility → delete)
- **Import cycle risk when splitting CLI**: Mitigate with lazy imports in command modules
- **litellm version incompatibility**: Mitigate by pinning version range and testing with Ollama, Anthropic, OpenAI

## Revision History
- **v1** (2026-02-07): Initial plan
- **v2** (2026-02-07): Addressed codex review feedback:
  - Split phase into 3 shippable milestones (1A/1B/1C)
  - Added staged config migration plan (shim → warning → utility → removal)
  - Added automated command-parity verification (help tree, option parity, smoke tests)
  - Switched from hand-rolled LLM adapters to litellm-first
  - Added typed Pydantic return models for LLMClient
  - Defined wrapper boundaries for litellm integration
