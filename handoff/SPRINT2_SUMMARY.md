# Sprint 2 Summary - Risk Aggregation & API Layer

**Status**: Ready to start
**Depends on**: Sprint 1 ✅ Complete
**Estimated Time**: 24-31 hours (3-4 days)

---

## Overview

Build on Sprint 1's evidence collection to compute actionable insights and serve via API.

---

## What We're Building

```
Sprint 1 Output:                    Sprint 2 Output:
~/.qaagent/runs/<run_id>/          ~/.qaagent/runs/<run_id>/
  evidence/                          evidence/
    quality.jsonl ────────────────►    quality.jsonl
    coverage.jsonl ───────────────►    coverage.jsonl
    churn.jsonl ──────────────────►    churn.jsonl
                                       risks.jsonl        ← NEW
                                       recommendations.jsonl  ← NEW

                                   API Server:
                                     GET /api/runs
                                     GET /api/runs/{id}/findings
                                     GET /api/runs/{id}/risks
                                     GET /api/runs/{id}/coverage
```

---

## Tasks (13 total)

### Phase 1: Foundation (1 task)
- S2-01: Evidence reader utilities

### Phase 2: Risk Aggregation (3 tasks)
- S2-02: Risk scoring models
- S2-03: Risk config loader
- S2-04: Risk aggregator core ⭐ **Core algorithm**

### Phase 3: Coverage-to-CUJ (2 tasks)
- S2-05: CUJ config loader
- S2-06: Coverage mapper

### Phase 4: Recommendations (1 task)
- S2-07: Recommendation generator

### Phase 5: API Layer (4 tasks)
- S2-08: FastAPI server setup
- S2-09: Runs endpoints
- S2-10: Evidence endpoints
- S2-11: CLI integration

### Phase 6: Testing & Docs (2 tasks)
- S2-12: Integration tests
- S2-13: Documentation

---

## Key Deliverables

**New Code**:
- `src/qaagent/analyzers/` - Risk aggregator, coverage mapper, recommender
- `src/qaagent/api/` - FastAPI server with REST endpoints
- `tests/integration/analyzers/` - Integration tests

**New CLI Commands**:
```bash
qaagent analyze risks              # Compute risk scores
qaagent analyze risks --run-id ID  # Analyze specific run
qaagent api                        # Start API server
```

**New API Endpoints**:
- `GET /api/runs` - List all runs
- `GET /api/runs/{id}` - Get run manifest
- `GET /api/runs/{id}/findings` - Get findings
- `GET /api/runs/{id}/coverage` - Get coverage
- `GET /api/runs/{id}/churn` - Get churn
- `GET /api/runs/{id}/risks` - Get top risks

---

## Risk Scoring Algorithm

```
For each file:
  1. Count security findings × 3.0 (security weight)
  2. Compute (1 - coverage) × 2.0 (coverage weight)
  3. Normalize churn × 2.0 (churn weight)
  4. Sum weighted scores
  5. Normalize to 0-100
  6. Assign band: P0 (≥80), P1 (≥65), P2 (≥50), P3 (<50)
  7. Compute confidence based on evidence diversity
```

---

## Coverage-to-CUJ Mapping

```yaml
# From cuj.yaml
journeys:
  - id: auth_login
    components: ["src/auth/*", "src/api/auth/*"]
    coverage_target: 80

# Algorithm:
1. Match component patterns to coverage records
2. Compute average coverage
3. Compare to target
4. Identify gaps
```

---

## Checkpoints

1. **After S2-03**: Evidence readers + risk models
2. **After S2-04**: Risk aggregation working ⭐
3. **After S2-07**: Coverage & recommendations
4. **After S2-11**: API layer complete
5. **After S2-13**: Sprint 2 complete

---

## Success Criteria

Sprint 2 is complete when:
- ✅ `qaagent analyze risks` computes risk scores
- ✅ risks.jsonl generated with valid records
- ✅ API serves all evidence via REST
- ✅ Coverage mapped to CUJs
- ✅ Recommendations generated
- ✅ All tests passing
- ✅ Documentation updated

---

## Usage Example

```bash
# 1. Collect evidence (Sprint 1)
qaagent analyze collectors /path/to/project

# 2. Compute risks (Sprint 2)
qaagent analyze risks

# 3. Start API server
qaagent api

# 4. Query API
curl http://localhost:8000/api/runs
curl http://localhost:8000/api/runs/<run_id>/risks

# 5. View top risk
curl http://localhost:8000/api/runs/<run_id>/risks | jq '.[0]'
```

Expected output:
```json
{
  "risk_id": "RSK-20251024-0001",
  "component": "src/auth/session.py",
  "score": 85.5,
  "band": "P0",
  "confidence": 0.8,
  "severity": "critical",
  "title": "Risk in src/auth/session.py",
  "factors": {
    "security": 45.0,
    "coverage": 30.0,
    "churn": 10.5
  },
  "recommendations": [
    "Add integration tests for authentication",
    "Review security findings: B101, B105"
  ]
}
```

---

## Dependencies

- ✅ Sprint 1 complete (all collectors working)
- ✅ risk_config.yaml exists
- ✅ cuj.yaml exists
- ✅ FastAPI, uvicorn, pyyaml installed

---

## Next Steps

1. **Codex**: Review Sprint 2 plan
2. **User**: Approve plan
3. **Codex**: Implement Phase 1-6
4. **Claude**: Review at checkpoints

---

## Links

- **Detailed Plan**: [SPRINT2_PLAN.md](./SPRINT2_PLAN.md)
- **Sprint 1 Summary**: [SPRINT1_SUMMARY.md](./SPRINT1_SUMMARY.md)
- **Risk Config**: [risk_config.yaml](./risk_config.yaml)
- **CUJ Config**: [cuj.yaml](./cuj.yaml)
