# Claude's Alignment Review — qaagent MVP Architecture

**Date:** 2025-10-24
**Reviewer:** Claude (Sonnet 4.5)
**Reviewed Artifacts:** CODEX_ANALYSIS_PLAN.md, EVIDENCE_STORE_SPEC.md, ANALYZERS_SPEC.md, SPRINT1_PLAN.md, risk_config.yaml, cuj.yaml

---

## Executive Summary

Codex has produced a **well-structured, thoughtful architecture** for the qaagent MVP. The core principles are sound:
- Local-first, privacy-respecting design
- Evidence-based analysis with clear data lineage
- Deterministic tooling with graceful degradation
- Modular architecture enabling incremental development

**Overall Assessment:** ✅ **APPROVED with refinements**

The plan is solid and ready to proceed with Sprint 1 after addressing the recommendations below. The architecture aligns well with the stated vision and constraints.

---

## What Works Well

### 1. **Evidence Store Design** ✅
The JSONL-based evidence store is excellent:
- **Append-friendly** for streaming results
- **Human-readable** for debugging and audit trails
- **Deterministic IDs** with clear prefixes (FND-, RSK-, COV-, etc.)
- **Proper separation** between raw artifacts and normalized evidence
- **Traceability** via `related_evidence` and `evidence_refs` fields

**Recommendation:** Proceed as designed. The optional SQLite backend can wait until post-MVP.

### 2. **Collector Abstraction** ✅
The Protocol-based collector interface is clean:
```python
class Collector(Protocol):
    def run(self, target: TargetContext, config: CollectorConfig) -> CollectorResult: ...
```

This provides:
- **Uniform interface** for all tools
- **Easy testing** with mocks
- **Graceful degradation** when tools are missing
- **Structured error handling**

### 3. **Risk Configuration Model** ✅
The `risk_config.yaml` with weighted scoring is well thought-out:
- Configurable weights for different risk dimensions
- Priority bands (P0-P3) for clear categorization
- Confidence modeling with multiple factors
- External AI disabled by default (privacy-first)

### 4. **Sprint Breakdown** ✅
Sprint 1 focus on evidence foundation before building higher-level features is the right approach. Getting the data layer correct first prevents costly refactoring later.

---

## Architectural Concerns & Recommendations

### 1. **Directory Structure Inconsistency** ⚠️

**Issue:** The plan proposes evidence storage under `~/.qaagent/runs/` but the existing codebase uses `~/.qaagent/workspace/<target>/` for outputs (see PROJECT_STATUS.md:8).

**Impact:** Potential confusion about where data lives; risk of duplicate storage patterns.

**Recommendation:**
```
~/.qaagent/
  workspace/<target>/          # Target-specific config, cache
    config.yaml
    cache/
  runs/                        # Cross-target run history
    <timestamp>/
      manifest.json
      evidence/
      artifacts/
  logs/                        # Optional structured logs
    <timestamp>.jsonl
```

This separates:
- **Workspace**: Target-specific configuration and cache (mutable)
- **Runs**: Immutable analysis snapshots (append-only)
- **Logs**: Optional debug/audit trail

### 2. **Git Churn Analysis Details Need Clarification** ⚠️

**Issue:** The spec mentions "90-day window, merge-base with origin/main" but doesn't address:
- What if `origin/main` doesn't exist? (e.g., `master`, `develop`, detached HEAD)
- What if the repo is <90 days old?
- What if there are no remote branches?

**Recommendation:** Add to ANALYZERS_SPEC.md:

```markdown
### Git Churn Heuristic Details

**Branch Detection (in priority order):**
1. If `origin/main` exists: merge-base with `origin/main`
2. Else if `origin/master` exists: merge-base with `origin/master`
3. Else if local `main` or `master` exists: use that branch
4. Else: use repository root commit as baseline

**Window Calculation:**
- Default: 90 calendar days from current date
- If repo is younger: use entire history
- Configurable via `qaagent.toml` or CLI flag: `--churn-window 60d`

**Edge Cases:**
- No commits in window: report zero churn, confidence=0.0
- Unmerged feature branches: only analyze commits reachable from HEAD
- No git repo: skip churn collector, mark executed=false
```

### 3. **API Layer Specification Missing** ⚠️

**Issue:** CODEX_ANALYSIS_PLAN mentions FastAPI endpoints but there's no detailed API specification.

**Recommendation:** Create `handoff/API_SPEC.md` with:
- Endpoint paths and methods
- Request/response schemas
- Query parameters (filtering, run selection)
- Error responses
- CORS policy (if any)
- Rate limiting (probably none for local-only MVP)

**Minimal Sprint 2 API:**
```
GET  /api/runs                    # List available runs
GET  /api/runs/{run_id}/manifest  # Run metadata
GET  /api/runs/{run_id}/findings  # Paginated findings
GET  /api/runs/{run_id}/risks     # Risk scores
GET  /api/runs/{run_id}/coverage  # Coverage metrics
GET  /api/runs/{run_id}/tests     # Test inventory
GET  /api/runs/{run_id}/apis      # API surface
GET  /api/latest/*                # Alias to most recent run
```

### 4. **Dependency Manifest Policy Incomplete** ⚠️

**Issue:** ANALYZERS_SPEC mentions TODO for poetry/pipenv support but doesn't specify fallback behavior.

**Recommendation:** Add to ANALYZERS_SPEC:

```markdown
### Dependency Analysis Policy

**Supported Formats (Priority Order):**
1. `requirements.txt`, `requirements*.txt` → pip-audit
2. `pyproject.toml` (with dependencies) → pip-audit via temp requirements
3. `poetry.lock` → safety (fallback) or pip-audit --from-poetry (if supported)
4. `Pipfile.lock` → safety (fallback)

**Behavior:**
- If multiple formats present: analyze all, merge findings with deduplication
- If no supported format: log diagnostic, skip dependency analysis
- Tool missing: diagnostic message with installation hint
- Transitive dependencies: analyze only locked/pinned versions for determinism
```

### 5. **Confidence Scoring Needs Formalization** ⚠️

**Issue:** risk_config.yaml defines confidence factors but doesn't specify the formula.

**Recommendation:** Add to EVIDENCE_STORE_SPEC or new RISK_SCORING.md:

```markdown
### Confidence Score Calculation

**Formula:**
```
confidence = base_confidence
           × (1 + evidence_density_bonus)
           × recency_factor
           × tool_diversity_factor
```

**Components:**
- `base_confidence`: Tool-specific (flake8=0.8, bandit=0.7, pip-audit=0.9)
- `evidence_density_bonus`: +0.1 per corroborating evidence (max +0.3)
- `recency_factor`: 1.0 if <7d old, 0.9 if <30d, 0.8 if >30d
- `tool_diversity_factor`: Based on config weight (0.1 per unique tool category)

**Caps:** confidence ∈ [0.0, 1.0]
```

---

## Documentation Improvements Needed

### 1. **Stub Files Require Expansion** 📝

The following files are essentially empty:
- `TASK_BOARD.md` - needs Sprint 1-3 breakdown
- `ACCEPTANCE_CRITERIA.md` - needs verifiable test cases
- `RUNBOOK.md` - needs complete setup and troubleshooting
- `PRIVACY_AND_AI_POLICY.md` - needs full policy text
- `PROMPT_GUIDELINES.md` - needs concrete templates

**Priority:** Expand these during Sprint 1 as implementation progresses.

### 2. **Missing Developer Documentation** 📝

**Need:** `docs/DEVELOPER_NOTES.md` explaining:
- Design decisions and trade-offs
- Module responsibilities
- Testing strategy
- How to add new collectors
- How to extend risk scoring
- Debugging techniques

**Action:** Create stub during Sprint 1 planning; expand during implementation.

### 3. **User-Facing Documentation Gap** 📝

**Need:** `docs/USER_GUIDE.md` for non-developers:
- What qaagent does (plain language)
- Installation and prerequisites
- First run walkthrough
- Interpreting results
- Common troubleshooting

**Action:** Draft post-Sprint 1; refine for MVP release.

---

## Implementation Recommendations

### 1. **Start with Minimal Viable Evidence Store** 🎯

**Sprint 1 Scope:**
- JSON-only (skip SQLite)
- Core record types: findings, coverage, churn, manifest
- Skip: risks.jsonl (that's Sprint 2), apis.jsonl (Sprint 2)
- Implement: run manager, ID generator, JSONL writer

**Rationale:** Get collectors working quickly; risk aggregation can consume JSON files in Sprint 2.

### 2. **Prioritize Collector Error Handling** 🎯

**Critical for MVP:** Graceful degradation when:
- Tool binaries are missing
- Tool execution times out
- Tool produces unexpected output format
- File system permissions issues

**Each collector should:**
1. Check for binary availability (`shutil.which()`)
2. Validate version compatibility
3. Set subprocess timeout
4. Catch parsing errors and log diagnostics
5. Return partial results when possible

### 3. **Logging Strategy** 🎯

**Structured logging schema:**
```python
{
    "timestamp": "2025-10-24T19:30:12Z",
    "run_id": "20251024_193012Z",
    "event": "collector.start",
    "tool": "flake8",
    "level": "info",
    "context": {"target": "/path/to/repo"}
}
```

**Log destinations:**
- Console: INFO and above (human-friendly)
- File: DEBUG and above (structured JSON)
- Evidence manifest: Summary stats only

### 4. **Testing Strategy** 🎯

**Three-tier approach:**

1. **Unit Tests** (fast, isolated)
   - Mock subprocess calls
   - Test parsing logic with fixtures
   - Validate ID generation, evidence writing

2. **Integration Tests** (moderate speed)
   - Use synthetic repo with known issues
   - Run real tools against controlled input
   - Verify evidence files match expectations

3. **End-to-End Tests** (slower, optional)
   - Run against real projects (examples/petstore-api)
   - Validate full pipeline
   - Compare with baseline snapshots

**Fixtures Repository:**
```
tests/fixtures/
  synthetic_repo/
    src/
      bugs.py          # Known flake8, pylint issues
      vulnerable.py    # Known bandit issues
    requirements.txt   # Known CVEs
    .git/             # Controlled git history
```

---

## Questions for User Clarification

### 1. **Existing Codebase Integration** ❓

The current `src/qaagent/` has:
- Route discovery and Next.js parsing
- Strategy generator
- Risk assessment (simple heuristics)
- OpenAPI generation
- Dashboard generator
- LLM wrapper

**Question:** Should we:
- **Option A:** Refactor existing code into new architecture (risky, slower)
- **Option B:** Build new modules alongside, deprecate old gradually (safer)
- **Option C:** Fresh start in new package, archive old as reference (cleanest)

**Recommendation:** Option B for MVP, Option A long-term. This preserves existing CLI commands while building the new foundation.

### 2. **Dashboard Technology** ❓

PROJECT_STATUS mentions "Enhanced Dashboard" with interactive HTML.

**Question:** For Sprint 3 dashboard:
- Reuse and adapt existing dashboard generator?
- Build new React-based SPA consuming API?
- Simple server-side rendered HTML with minimal JS?

**Recommendation:** Adapt existing enhanced dashboard to consume API endpoints. This is fastest path to MVP while maintaining interactivity.

### 3. **Ollama Integration Timing** ❓

PROJECT_STATUS mentions Ollama integration as next step, but Codex's plan pushes AI to Sprint 3.

**Question:** Is local AI summarization:
- Sprint 3 priority (as per Codex plan)?
- Post-MVP enhancement?
- Critical for initial launch?

**Recommendation:** Stick with Sprint 3. Get evidence foundation solid first.

---

## Alignment with Codex

### Areas of Agreement ✅

1. **Evidence-first architecture**: Build the data layer before the analysis layer
2. **Deterministic tooling**: Pinned versions, reproducible results
3. **Privacy-first**: Local-only by default, explicit opt-in for external services
4. **Graceful degradation**: Missing tools should not break the entire pipeline
5. **Sprint phasing**: Foundation → Analysis → Polish

### Suggested Adjustments 📋

1. **Clarify directory structure** to avoid conflicts with existing workspace system
2. **Formalize git churn heuristic** with edge case handling
3. **Add API specification** before starting Sprint 2 work
4. **Document confidence formula** to ensure consistent implementation
5. **Expand stub documentation** incrementally during Sprint 1

### No Objections ✅

- Collector abstraction design
- Evidence store schema
- Risk config model
- Sprint 1 task breakdown
- Tool selection (flake8, pylint, bandit, pip-audit)

---

## Next Steps

### Immediate (Before Sprint 1 Implementation)

1. **User to confirm:**
   - Directory structure approach (workspace vs runs)
   - Existing codebase integration strategy (Option A/B/C)
   - Dashboard technology choice

2. **Claude to create:**
   - `API_SPEC.md` with detailed endpoint definitions
   - `RISK_SCORING.md` with formalized confidence formula
   - `docs/DEVELOPER_NOTES.md` stub with architecture decisions

3. **Codex to create:**
   - Synthetic test repository under `tests/fixtures/synthetic_repo/`
   - Git churn heuristic edge case handling spec
   - Dependency manifest detection logic spec

4. **Joint review:**
   - Validate expanded specs address concerns
   - Sign off on Sprint 1 task list
   - Establish collaboration workflow (Claude docs/review, Codex implementation)

### Sprint 1 Execution

- **Codex leads:** Implementation of collectors, evidence store, CLI orchestration
- **Claude supports:** Documentation expansion, code review, test case design, troubleshooting
- **Checkpoints:** After each major deliverable (S1-03, S1-10, S1-13)

---

## Conclusion

Codex has laid excellent groundwork. The architecture is sound, the sprint plan is reasonable, and the evidence-first approach is exactly right for building a maintainable, extensible QA platform.

**Primary recommendation:** Proceed with Sprint 1 after addressing the directory structure question and creating the missing API specification. The other concerns are refinements that can be handled during implementation.

**Confidence in plan:** 9/10 (high confidence with minor clarifications needed)

Let's build this! 🚀

---

**Approval Status:** ✅ **APPROVED TO PROCEED** pending user confirmation on 3 questions above.
