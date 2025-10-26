# Codex Startup - Sprint 1 Ready

**Date:** 2025-10-24
**Status:** 🟢 **ALL DECISIONS APPROVED - BEGIN SPRINT 1**

---

## Welcome Back, Codex!

Claude has reviewed your architectural plan and **approves it fully**. All blocking questions have been answered. You're cleared to start Sprint 1 implementation.

---

## ✅ Approved Architecture Decisions

### 1. Directory Structure (APPROVED)

Implement this exact structure:

```
~/.qaagent/
  workspace/<target>/          # Target-specific config, cache (mutable)
    config.yaml
    cache/

  runs/                        # Cross-target run history (immutable, append-only)
    <YYYYMMDD_HHMMSSZ>/       # Example: 20251024_193012Z
      manifest.json
      evidence/
        findings.jsonl
        risks.jsonl          # Sprint 2
        coverage.jsonl
        tests.jsonl          # Sprint 2
        quality.jsonl
        churn.jsonl
        apis.jsonl           # Sprint 2
      artifacts/
        flake8.log
        pylint.json
        bandit.json
        pip_audit.json
        coverage.xml
        git_shortstat.txt

  logs/                        # Optional structured logs
    <YYYYMMDD_HHMMSSZ>.jsonl

  config/                      # Global configuration
    risk_config.yaml
    privacy.yaml
    secrets.yaml
```

**Key points:**
- Use `runs/` for all analysis output (not `workspace/`)
- `workspace/<target>/` is for target-specific configs only
- Evidence store writes to `~/.qaagent/runs/<timestamp>/`

---

### 2. Existing Codebase (APPROVED)

**Approach:** Build new modules alongside existing code

```
src/qaagent/
  # NEW MODULES (you create in Sprint 1)
  collectors/          # S1-04 to S1-09
    __init__.py
    flake8.py
    pylint.py
    bandit.py
    pip_audit.py
    coverage.py
    git_churn.py

  evidence/            # S1-01 to S1-03
    __init__.py
    models.py          # Evidence dataclasses
    run_manager.py     # Create runs, manage directories
    writer.py          # JSONL writer

  # EXISTING MODULES (keep, don't modify yet)
  discovery/           # Next.js parser - keep
  openapi_gen/         # Keep
  config/              # Extend later
  analyzers/           # Extend in Sprint 2
  dashboard/           # Adapt in Sprint 3
  llm/                 # Extend in Sprint 3
```

**Don't break existing functionality** - add new, deprecate old later.

---

### 3. Dashboard (APPROVED - Sprint 3)

Reuse existing enhanced dashboard, adapt to consume API endpoints.

---

## 📋 Your Pre-Sprint 1 Checklist

Before writing code, complete these tasks:

### 1. Create Synthetic Test Repository ✅

**Location:** `tests/fixtures/synthetic_repo/`

**Contents:**
```
tests/fixtures/synthetic_repo/
  src/
    good_code.py           # No issues (control)
    style_issues.py        # 3x flake8 E302 violations
    security_issue.py      # 1x bandit B101 (hard-coded password)
    auth/
      __init__.py
      session.py           # For git churn testing

  requirements.txt         # Include package with known CVE
                          # Example: django==2.2.0 (CVE-2019-12781)

  coverage.xml            # Mock coverage file showing 65% line coverage

  .git/                   # Initialize git repo with controlled history
                          # - Initial commit 100 days ago
                          # - 14 commits to auth/session.py in last 90 days
                          # - 420 lines added, 318 deleted
```

**Script to generate:**
```bash
#!/bin/bash
# tests/fixtures/create_synthetic_repo.sh

cd tests/fixtures
mkdir -p synthetic_repo/src/auth
cd synthetic_repo

# Create files with known issues
cat > src/style_issues.py << 'EOF'
import os
def foo():
    pass
def bar():  # E302: expected 2 blank lines
    pass
def baz():  # E302: expected 2 blank lines
    pass
EOF

cat > src/security_issue.py << 'EOF'
# B101: hard-coded password
password = "admin123"  # nosec would disable, but we want to test
EOF

cat > requirements.txt << 'EOF'
django==2.2.0
requests==2.25.0
EOF

# Initialize git with history
git init
git add .
git commit -m "Initial commit" --date="2024-07-15T12:00:00"

# Add commits to auth/session.py for churn
for i in {1..14}; do
    echo "# Change $i" >> src/auth/session.py
    git add src/auth/session.py
    git commit -m "Update session handling $i" --date="2024-08-$(($i+10))T12:00:00"
done

echo "✅ Synthetic repo created"
```

---

### 2. Document Edge Cases ✅

**Update:** `handoff/ANALYZERS_SPEC.md`

Add this section after line 36 (Git churn section):

```markdown
### Git Churn Heuristic Details

**Branch Detection (priority order):**
1. If `origin/main` exists: merge-base with `origin/main`
2. Else if `origin/master` exists: merge-base with `origin/master`
3. Else if local `main` exists: use local `main`
4. Else if local `master` exists: use local `master`
5. Else: use repository root commit as baseline

**Window Calculation:**
- Default: 90 calendar days from current date
- If repo younger than 90 days: use entire history
- Configurable via CLI: `--churn-window 30d` or config

**Edge Cases:**
- No commits in window: report zero churn, confidence=0.0
- Detached HEAD: analyze from HEAD
- No remote configured: use local branches only
- Not a git repo: skip collector, mark executed=false

**Example:**
```bash
# Get merge-base
git merge-base HEAD origin/main || git merge-base HEAD main || git rev-list --max-parents=0 HEAD

# Get commits in window
git log --since="90 days ago" --stat --format="%H|%aI"
```
```

**And add dependency manifest policy after line 33:**

```markdown
### Dependency Analysis Policy

**Supported Formats (priority order):**
1. `requirements.txt`, `requirements-*.txt` → pip-audit
2. `pyproject.toml` with `[project.dependencies]` → extract to temp requirements, run pip-audit
3. `poetry.lock` → run pip-audit (if version supports --from-poetry)
4. `Pipfile.lock` → log "poetry/pipenv detected, use pip-audit or safety manually"

**Behavior:**
- Multiple formats present: analyze all, deduplicate findings by CVE ID
- No supported format found: log diagnostic, skip dependency analysis
- pip-audit missing: try safety as fallback
- Both missing: diagnostic only, don't fail

**Example diagnostic messages:**
- "requirements.txt not found, skipping dependency analysis"
- "poetry.lock found but pip-audit doesn't support it; consider exporting requirements.txt"
```

---

### 3. Review Claude's New Specs ✅

**Read and approve (or request changes):**

1. **`handoff/API_SPEC.md`** - REST API design for Sprint 2
   - Does the endpoint structure work?
   - Are the query parameters sufficient?

2. **`handoff/RISK_SCORING.md`** - Risk calculation formulas
   - Are the formulas implementable?
   - Any concerns with the normalization strategies?

3. **Expanded documentation:**
   - RUNBOOK.md
   - ACCEPTANCE_CRITERIA.md
   - PRIVACY_AND_AI_POLICY.md
   - PROMPT_GUIDELINES.md

**If you have concerns,** flag them now before implementation.

---

## 🚀 Sprint 1 Implementation Order

Once pre-work is done, follow this sequence from `SPRINT1_PLAN.md`:

### Phase 1: Foundation (S1-01 to S1-03)
```
S1-01: Evidence data models (0.5d)
  ├─ Create src/qaagent/evidence/models.py
  ├─ Define Finding, Manifest, CollectorResult dataclasses
  └─ Unit tests for model validation

S1-02: Run manager (0.5d)
  ├─ Create src/qaagent/evidence/run_manager.py
  ├─ Implement directory creation (~/.qaagent/runs/<timestamp>/)
  ├─ Implement ID generator (EvidenceIDGenerator class)
  └─ Unit tests

S1-03: JSON writer (0.5d)
  ├─ Create src/qaagent/evidence/writer.py
  ├─ Implement JSONL streaming writer
  └─ Unit tests
```

**Checkpoint:** After S1-03, validate that:
- Directories are created correctly
- IDs are generated properly (FND-20251024-0001 format)
- JSONL files are valid JSON Lines

---

### Phase 2: Collectors (S1-04 to S1-09)

Start with **flake8 as proof-of-concept:**

```
S1-04: flake8 collector (0.5d)
  ├─ Create src/qaagent/collectors/flake8.py
  ├─ Implement Collector protocol
  ├─ Parse JSON output to Finding records
  ├─ Write to evidence store via writer
  └─ Integration test with synthetic_repo
```

**Checkpoint:** After S1-04, validate:
- flake8 finds the 3 E302 violations in synthetic_repo
- Findings are written to quality.jsonl correctly
- Manifest records tool execution

**Then parallelize remaining collectors** (or do sequentially):
- S1-05: pylint
- S1-06: bandit (must find B101 in synthetic_repo)
- S1-07: pip-audit (must find CVE in requirements.txt)
- S1-08: coverage (parse coverage.xml)
- S1-09: git churn (use documented edge case logic)

---

### Phase 3: Orchestration (S1-10 to S1-14)

```
S1-10: Analyzer orchestrator (0.5d)
  ├─ Coordinate all collectors
  ├─ Handle failures gracefully
  └─ Write consolidated manifest

S1-11: CLI command (0.5d)
  ├─ `qaagent analyze` command
  ├─ Progress display
  └─ Summary output

S1-12: Structured logging (0.25d)
  ├─ JSON logging to ~/.qaagent/logs/
  └─ Console output formatting

S1-13: Unit tests (0.75d)
  └─ Full test coverage of Sprint 1 code

S1-14: Docs update (0.5d)
  └─ Update RUNBOOK with actual commands/setup
```

---

## 📚 Key Documents Reference

| Document | Purpose | Your Action |
|----------|---------|-------------|
| **DECISIONS.md** | Approved architecture | ✅ Follow this |
| **SPRINT1_PLAN.md** | Task breakdown | 📋 Your roadmap |
| **EVIDENCE_STORE_SPEC.md** | Evidence schema | 📖 Implement this |
| **ANALYZERS_SPEC.md** | Collector interfaces | 📖 Implement + add edge cases |
| **API_SPEC.md** | API design (Sprint 2) | 👀 Review & approve |
| **RISK_SCORING.md** | Risk formulas (Sprint 2) | 👀 Review & approve |
| **CLAUDE_ALIGNMENT_REVIEW.md** | Claude's full review | 📖 Read for context |
| **RUNBOOK.md** | User guide | 📝 Update in S1-14 |
| **ACCEPTANCE_CRITERIA.md** | Definition of Done | ✅ Test against this |

---

## 💬 Communication Checkpoints

**After completing pre-work:**
- Notify user that synthetic repo is ready
- Confirm you've reviewed API_SPEC and RISK_SCORING
- Flag any concerns before coding

**During Sprint 1:**
- Checkpoint after S1-03 (evidence store working?)
- Checkpoint after S1-04 (first collector working?)
- Checkpoint after S1-10 (all collectors integrated?)

**After Sprint 1:**
- Run full test suite against acceptance criteria
- Update DEVELOPER_NOTES with lessons learned
- Hand back to Claude/user for review

---

## 🎯 Success Criteria

Sprint 1 is complete when:

- ✅ `qaagent analyze` runs against synthetic_repo
- ✅ Finds 3 flake8 violations
- ✅ Finds 1 bandit B101 issue
- ✅ Finds CVE in requirements.txt
- ✅ Parses coverage.xml correctly (65%)
- ✅ Calculates git churn for auth/session.py (14 commits)
- ✅ All evidence written to `~/.qaagent/runs/<timestamp>/`
- ✅ Manifest.json is valid and complete
- ✅ Tests pass (S1-13)

---

## ⚠️ Important Reminders

1. **Use approved directory structure** - `~/.qaagent/runs/`, not `workspace/<target>/runs/`
2. **Don't break existing code** - add new modules, don't refactor old yet
3. **Graceful degradation** - missing tools should warn, not fail
4. **Test with synthetic_repo** - must find known issues
5. **Document as you go** - update DEVELOPER_NOTES with decisions

---

## 🚦 Status

- 🟢 **Architecture:** Approved
- 🟢 **Directory structure:** Approved
- 🟢 **Integration approach:** Approved
- 🟡 **Pre-work:** Pending (synthetic repo, edge case docs)
- ⚪ **Implementation:** Not started

**Next action:** Complete pre-work checklist above, then begin S1-01.

---

Good luck! You've got a solid plan. Execute it. 🚀

**Questions?** Refer to CLAUDE_ALIGNMENT_REVIEW.md or ask user/Claude.
