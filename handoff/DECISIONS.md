# Architecture Decisions

**Date:** 2025-10-24
**Participants:** User, Claude, Codex

---

## Decision 1: Directory Structure ✅

**Status:** APPROVED

**Structure:**
```
~/.qaagent/
  workspace/<target>/    # Target configs (mutable)
  runs/<timestamp>/      # Analysis snapshots (immutable)
  logs/                  # Debug logs
  config/                # Global preferences
```

**Rationale:**
- Separates mutable workspace from immutable runs
- Enables historical comparison and audit trails
- Prevents config changes from affecting past analysis

**Approved by:** User (2025-10-24)

---

## Decision 2: Existing Codebase Integration ✅

**Status:** APPROVED

**Approach:** Option B - Build new modules alongside, deprecate old gradually

**Implementation:**
- Sprint 1: New `collectors/` and `evidence/` modules
- Sprint 2: Extend existing `analyzers/` with new risk engine
- Sprint 3: Adapt existing dashboard to consume new API
- Post-MVP: Deprecate old modules with warnings

**Rationale:**
- Minimizes risk by keeping existing functionality working
- Allows incremental migration and validation
- Users can continue using current features during transition

**Approved by:** User (2025-10-24)

---

## Decision 3: Dashboard Technology ✅

**Status:** APPROVED

**Approach:** Option 1 - Reuse existing enhanced dashboard, adapt to consume API

**Implementation:**
- Keep existing HTML/CSS/JS assets
- Replace data source from embedded HTML to API fetch calls
- Add run selector dropdown
- Minimal JavaScript changes

**Rationale:**
- Fastest path to MVP (reuses existing UI work)
- Familiar interface for users
- Lower implementation risk than building from scratch

**Approved by:** User (2025-10-24)

---

## Next Steps

With these decisions locked in, Codex can proceed with Sprint 1:

### Pre-Sprint 1 (Codex)
- [ ] Create synthetic test repository (`tests/fixtures/synthetic_repo/`)
- [ ] Document git churn edge cases in ANALYZERS_SPEC.md
- [ ] Finalize dependency manifest detection logic
- [ ] Review and sign off on Claude's specs (API_SPEC, RISK_SCORING)

### Sprint 1 Start
- [ ] Implement evidence store with approved directory structure
- [ ] Build collectors using new module structure (alongside existing code)
- [ ] Set up integration tests with synthetic repo
- [ ] Checkpoint after S1-03 to validate approach

**Status:** 🟢 **READY TO BEGIN SPRINT 1**
