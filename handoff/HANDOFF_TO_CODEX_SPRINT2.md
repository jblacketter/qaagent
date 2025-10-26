# Handoff to Codex: Sprint 2

**From**: Claude
**To**: Codex
**Date**: 2025-10-24
**Subject**: Sprint 2 Plan Ready for Implementation

---

## Status

✅ **Sprint 1 Complete** - All collectors working, tests passing (9.5/10 quality)
📋 **Sprint 2 Planned** - Ready for your review and implementation

---

## What I Did

1. **Completed Sprint 1 Review**:
   - Reviewed coverage collector, git churn collector, orchestrator, CLI integration
   - All tests passing (10 passed, 3 skipped)
   - Created comprehensive review: `CLAUDE_SPRINT1_COMPLETE.md`
   - Score: 9.5/10 - Production ready

2. **Created Sprint 2 Plan**:
   - Detailed task breakdown (13 tasks across 6 phases)
   - Clear acceptance criteria for each task
   - 5 checkpoint moments for review
   - Estimated timeline: 24-31 hours (3-4 days)

---

## Documents Created

| File | Purpose |
|------|---------|
| `SPRINT2_PLAN.md` | Comprehensive task breakdown with implementation details |
| `SPRINT2_SUMMARY.md` | Quick reference summary |
| `CLAUDE_SPRINT1_COMPLETE.md` | Final Sprint 1 review (9.5/10) |
| `SPRINT1_SUMMARY.md` | Sprint 1 quick reference |
| `HANDOFF_TO_CODEX_SPRINT2.md` | This document |

---

## Sprint 2 Overview

### Goal
Build on Sprint 1's evidence collection to compute actionable insights and serve via API.

### What You'll Build

**Core Components**:
1. **Risk Aggregator** - Read evidence, apply weights, generate risk scores
2. **Coverage Mapper** - Map coverage to CUJs, identify gaps
3. **Recommendation Engine** - Generate testing priorities
4. **API Server** - FastAPI to serve evidence and analysis

**New CLI Commands**:
- `qaagent analyze risks` - Compute risk scores from evidence
- `qaagent api` - Start API server (future task)

**New Evidence**:
- `risks.jsonl` - Computed risk scores per component
- `recommendations.jsonl` - Testing recommendations

---

## Task Breakdown

### Phase 1: Foundation (S2-01)
Create evidence reader utilities to load JSONL files.

**Complexity**: Low (1-2 hours)

### Phase 2: Risk Aggregation (S2-02 to S2-04) ⭐
- Define risk models
- Load risk_config.yaml
- **Core task**: Implement risk scoring algorithm

**Complexity**: Medium-High (6-8 hours)
**Checkpoint after this phase**

### Phase 3: Coverage-to-CUJ (S2-05 to S2-06)
- Load cuj.yaml
- Map coverage records to CUJs using glob patterns
- Identify coverage gaps

**Complexity**: Medium (4-6 hours)

### Phase 4: Recommendations (S2-07)
Generate actionable recommendations from risks and coverage gaps.

**Complexity**: Medium (2-3 hours)
**Checkpoint after this phase**

### Phase 5: API Layer (S2-08 to S2-11)
- FastAPI server setup
- Endpoints for runs, evidence, risks
- CLI integration

**Complexity**: Medium (5-6 hours)
**Checkpoint after this phase**

### Phase 6: Testing & Docs (S2-12 to S2-13)
Integration tests and documentation updates.

**Complexity**: Medium (6 hours)

---

## Risk Scoring Algorithm (Core Logic)

```python
# Pseudocode for S2-04

for each file:
    security_score = count_findings(severity in ["critical", "high"]) × 3.0
    coverage_score = (1 - coverage_value) × 2.0
    churn_score = normalize(commits + lines_changed) × 2.0

    total_score = security_score + coverage_score + churn_score
    normalized_score = min(total_score, 100)

    if normalized_score >= 80: band = "P0"
    elif normalized_score >= 65: band = "P1"
    elif normalized_score >= 50: band = "P2"
    else: band = "P3"

    confidence = count_present_factors / total_factors
```

---

## Key Design Decisions

### 1. Evidence Reader Pattern
Same pattern as collectors - graceful degradation:
```python
class EvidenceReader:
    def read_findings(self) -> List[FindingRecord]:
        if not file.exists():
            return []  # Empty list, not error
        return parse_jsonl(file)
```

### 2. Risk Granularity
**Sprint 2**: File-level risks (simpler)
**Sprint 3**: CUJ-level and API endpoint risks (more complex)

### 3. API Design
**Read-only**: No mutations via API
**Pagination**: Not for MVP (add TODO if needed)
**CORS**: Enabled for dashboard

### 4. Configuration
**Load from**: `handoff/risk_config.yaml` and `handoff/cuj.yaml` for now
**Future**: Copy to `~/.qaagent/config/` for user customization

---

## Checkpoints for Claude Review

1. **After S2-03**: Evidence readers + risk models working
2. **After S2-04**: Risk aggregation complete ⭐ (most important)
3. **After S2-07**: Coverage & recommendations working
4. **After S2-11**: API layer complete
5. **After S2-13**: Sprint 2 final review

**When to pause**: After each checkpoint, wait for Claude to review before proceeding.

---

## What's Already Done (Sprint 1)

You have a solid foundation:
- ✅ Evidence store (models, run manager, writer, ID generator)
- ✅ 6 collectors (flake8, pylint, bandit, pip-audit, coverage, git churn)
- ✅ Orchestrator
- ✅ CLI integration
- ✅ All tests passing

Evidence is stored in:
```
~/.qaagent/runs/<run_id>/
  manifest.json
  evidence/
    quality.jsonl
    coverage.jsonl
    churn.jsonl
  artifacts/
    *.json, *.log
```

You just need to **read** this evidence and **analyze** it.

---

## Questions to Resolve Before Starting

1. **Should RunManager have `load_run(run_id)` method?**
   - **Answer**: Yes, add it. It should return a RunHandle for an existing run.

2. **Where to load risk_config.yaml and cuj.yaml from?**
   - **Answer**: From `handoff/` directory for now. Add TODO to copy to `~/.qaagent/config/` in Sprint 3.

3. **Should API have pagination?**
   - **Answer**: Not for MVP. Add TODO comment if needed for large datasets.

4. **How to handle missing evidence files?**
   - **Answer**: Return empty list, log diagnostic. Same pattern as collectors.

---

## Next Steps

1. **You (Codex)**: Read Sprint 2 plan thoroughly
2. **You (Codex)**: Ask clarifying questions if anything is unclear
3. **User**: Approve plan
4. **You (Codex)**: Begin implementation starting with S2-01
5. **Claude**: Review at checkpoints

---

## Notes for You

**Follow Sprint 1 Quality**:
- Same error handling patterns (try/except with graceful degradation)
- Same test strategy (unit + integration)
- Same documentation approach (update DEVELOPER_NOTES.md as you go)
- Same code quality (type hints, docstrings, clean separation)

**Keep It Simple**:
- Don't over-engineer
- File-level risks first (not CUJ-level yet)
- Rule-based recommendations (not LLM-generated yet)
- Read-only API (no mutations)

**When Stuck**:
- Pause and ask questions
- Don't make architectural decisions alone
- Wait for checkpoint reviews

**Testing**:
- Use synthetic repo from Sprint 1
- Integration tests validate full pipeline
- All collectors → risks → API

---

## Expected Outcomes

After Sprint 2, users will be able to:

```bash
# 1. Collect evidence
qaagent analyze collectors /path/to/project

# 2. Analyze risks
qaagent analyze risks

# Output:
# Generated 42 risk records
# Top risk: src/auth/session.py (score: 85.5)

# 3. Start API
qaagent api

# 4. Query via curl
curl http://localhost:8000/api/runs
curl http://localhost:8000/api/runs/20251024_193012Z/risks | jq '.[0]'

# Output:
# {
#   "risk_id": "RSK-20251024-0001",
#   "component": "src/auth/session.py",
#   "score": 85.5,
#   "band": "P0",
#   "confidence": 0.8,
#   "factors": {
#     "security": 45.0,
#     "coverage": 30.0,
#     "churn": 10.5
#   }
# }
```

---

## Success Criteria

Sprint 2 is done when:
- ✅ User can run `qaagent analyze risks` on existing run
- ✅ risks.jsonl generated with valid risk records
- ✅ API server serves all evidence
- ✅ Coverage mapped to CUJs with gaps identified
- ✅ Recommendations generated
- ✅ All tests passing
- ✅ Documentation updated

---

## Good Luck! 🚀

You did an excellent job on Sprint 1 (9.5/10). I'm confident Sprint 2 will be equally strong.

Remember:
- **Pause at checkpoints** - Don't rush ahead
- **Ask questions** - Better to clarify than assume
- **Keep it simple** - MVP quality, not over-engineered

I'll be ready to review at each checkpoint.

---

**Ready when you are!**

— Claude
