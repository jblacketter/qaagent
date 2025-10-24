# Agent Collaboration Workflow

**Purpose**: This document explains how Claude (analysis/review) and Codex (implementation) collaborate on this project.

---

## Overview

This project uses a **dual-agent workflow** to maintain high quality while moving quickly:

```
┌─────────────────────────────────────────────────────────────┐
│                    User (You)                               │
│  - Defines goals and requirements                           │
│  - Reviews and approves deliverables                        │
│  - Final testing and validation                             │
└───────────┬──────────────────────────┬──────────────────────┘
            │                          │
            ▼                          ▼
    ┌───────────────┐          ┌───────────────┐
    │ Claude Agent  │◄────────►│ Codex Agent   │
    │ (Analysis)    │  Iterate │ (Implement)   │
    └───────────────┘          └───────────────┘
```

### Agent Roles

| Agent | Role | Strengths | Tools |
|-------|------|-----------|-------|
| **Claude** | Analyzer & Reviewer | Deep analysis, architectural thinking, documentation | Claude Code (via VSCode) |
| **Codex** | Implementer | Fast coding, refactoring, test writing | Cursor IDE |
| **You** | Director & Validator | Domain knowledge, final decisions, Mac testing | Terminal, Browser |

---

## The 5-Step Process

### Step 1: Analysis (Claude)
**Who**: Claude
**Input**: User request or issue
**Output**: Analysis document (e.g., `docs/PHASE_X_ANALYSIS.md`)

**Claude's Tasks:**
1. Read relevant existing code
2. Understand the problem deeply
3. Research alternatives
4. Identify constraints and risks
5. Propose solution approach
6. Define success criteria
7. Create checklist for Codex

**Deliverable**: Structured markdown document with:
- Executive summary
- Current state analysis
- Recommended approach
- Technical details
- Questions for Codex
- Success criteria

**Example**: [docs/PHASE_1_ANALYSIS.md](PHASE_1_ANALYSIS.md)

---

### Step 2: Review & Enhancement (Codex)
**Who**: Codex
**Input**: Claude's analysis document
**Output**: Enhanced implementation plan

**Codex's Tasks:**
1. Read Claude's analysis thoroughly
2. Identify gaps or unclear areas
3. Propose implementation approach
4. Answer Claude's questions
5. Suggest improvements to the plan
6. Identify potential issues
7. Estimate effort more precisely

**Deliverable**: Response document or comments with:
- Agreement/disagreement with approach
- Specific implementation strategy
- Answers to Claude's questions
- Additional considerations
- Revised estimates if needed

**Template**:
```markdown
## Review of {Analysis Name}

### Summary
[Quick take - agree/partially agree/disagree]

### Strengths
- What's good about the proposal

### Concerns
- What needs clarification
- Potential issues

### Implementation Approach
- How I plan to build it
- File structure
- Key decisions

### Answers to Questions
1. Question 1: My answer
2. Question 2: My answer

### Counterproposals
[If I have different/better ideas]

### Ready to Implement?
[Yes/No - if no, what's blocking]
```

---

### Step 3: Iteration (Claude ↔ Codex)
**Who**: Both agents
**Input**: Each other's feedback
**Output**: Agreed implementation plan

**Process:**
1. Codex reviews Claude's analysis
2. Claude reviews Codex's plan
3. Both discuss trade-offs
4. Iterate until consensus
5. Document final agreement

**How to Iterate:**
- Claude asks clarifying questions
- Codex provides more details
- Both agents refine the approach
- Continue until both say "ready to implement"

**Signs of Readiness:**
- ✅ No major open questions
- ✅ Implementation approach is clear
- ✅ Both agents agree on scope
- ✅ Success criteria are measurable
- ✅ Risks are identified and mitigated

---

### Step 4: Implementation (Codex)
**Who**: Codex
**Input**: Agreed plan
**Output**: Working code with tests

**Codex's Tasks:**
1. Implement according to agreed design
2. Write unit tests
3. Write integration tests
4. Update documentation
5. Create/update examples
6. Self-review before submitting
7. Run all checks locally

**Pre-Submission Checklist:**
```bash
# Tests pass
pytest -v

# Code quality
ruff check src/ tests/
black src/ tests/
mypy src/

# Manual testing
qaagent {new-command} --help
qaagent {new-command} {test-args}

# Git is clean
git status  # No debug code, commented lines
```

**Deliverable**: Pull request or commit with:
- Implementation code
- Tests (unit + integration)
- Updated docs
- Example usage
- Clear commit messages

---

### Step 5: Review & Testing (Claude + User)
**Who**: Claude reviews, User validates
**Input**: Codex's implementation
**Output**: Approved code or change requests

**Claude's Review Tasks:**
1. Code review (architecture, patterns, style)
2. Test review (coverage, edge cases)
3. Documentation review (accuracy, completeness)
4. Try the feature manually
5. Check against success criteria
6. Provide feedback to Codex

**Claude's Review Template:**
```markdown
## Review of {Feature Name}

### Summary
[Pass/Needs Changes/Reject]

### What Works Well
- List strengths

### Issues Found
Priority 1 (Must Fix):
- Issue 1
- Issue 2

Priority 2 (Should Fix):
- Issue 3

Priority 3 (Nice to Have):
- Issue 4

### Testing Results
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing: {result}
- [ ] Examples work

### Documentation Check
- [ ] README updated
- [ ] Docstrings present
- [ ] Example added

### Questions
- Any clarifications needed

### Recommendation
[Approve / Request Changes / Needs Discussion]
```

**User's Validation Tasks:**
1. Pull changes to Mac M1
2. Follow test instructions
3. Verify on actual target platform
4. Check user experience
5. Approve or request changes

---

## Communication Standards

### File Locations
```
qaagent/
├── .claud                    # Claude's instructions
├── .cursorrules              # Codex's instructions
├── docs/
│   ├── AGENT_WORKFLOW.md     # This file
│   ├── PHASE_X_ANALYSIS.md   # Analysis documents
│   └── REVIEWS/              # Review documents
│       └── review_{feature}.md
```

### Document Naming
- Analysis: `PHASE_X_ANALYSIS.md` or `{feature}_ANALYSIS.md`
- Review: `review_{feature}_YYYYMMDD.md`
- Decisions: `ADR_{number}_{title}.md` (Architecture Decision Records)

### Markdown Format
All documents use:
- Clear headings (##, ###)
- Checklists for tasks
- Tables for comparisons
- Code blocks for examples
- **Bold** for emphasis
- `code` for technical terms

---

## Decision Making

### When Agents Disagree

**Scenario**: Claude and Codex have different opinions

**Resolution Process:**
1. Both agents state their position clearly
2. Each provides reasoning and trade-offs
3. Identify if it's a:
   - **Technical disagreement**: Prototype both approaches
   - **Scope disagreement**: Escalate to User
   - **Priority disagreement**: Refer to project goals
4. User makes final decision if needed

**Example**:
```markdown
## Disagreement: How to Structure Examples

### Claude's Position
Create one comprehensive example covering all features.

Reasoning:
- Easier to maintain
- Shows integration
- Less duplication

### Codex's Position
Create multiple small examples, one per feature.

Reasoning:
- Easier to understand
- Faster to try
- Better for docs

### User Decision Needed
Which approach aligns better with project goals?
```

### Escalation to User

**When to Escalate:**
- Agents can't reach consensus after 2-3 iterations
- Decision impacts project direction
- Requires domain knowledge
- Has significant time/cost implications
- Involves external dependencies

**How to Escalate:**
Both agents prepare a summary for the user with:
1. The question/decision
2. Each agent's position
3. Trade-offs of each approach
4. Recommendation (if any)
5. Impact of delay

---

## Quality Gates

### Before Moving to Next Phase
All must be ✅:
- [ ] Analysis is complete and clear
- [ ] Implementation plan is agreed
- [ ] Code is written and tested
- [ ] Claude has reviewed and approved
- [ ] User has validated on Mac M1
- [ ] Documentation is updated
- [ ] Success criteria are met

### Red Flags
Stop and revisit if you see:
- 🚩 Unclear requirements
- 🚩 Disagreement between agents
- 🚩 Tests failing
- 🚩 Breaking changes without migration
- 🚩 Scope creep
- 🚩 Missing documentation

---

## Tips for Effective Collaboration

### For Claude
- ✓ Be specific in analysis (not vague)
- ✓ Provide examples and code snippets
- ✓ Anticipate implementation challenges
- ✓ Ask Codex targeted questions
- ✓ Review thoroughly but constructively
- ✗ Don't micro-manage implementation details
- ✗ Don't approve without testing

### For Codex
- ✓ Ask clarifying questions early
- ✓ Propose alternatives if you see issues
- ✓ Write tests before claiming done
- ✓ Self-review rigorously
- ✓ Document your decisions
- ✗ Don't implement without clear spec
- ✗ Don't skip tests for speed

### For User
- ✓ Provide clear requirements
- ✓ Give agents time to iterate
- ✓ Test on actual Mac M1
- ✓ Provide specific feedback
- ✓ Make decisions when escalated
- ✗ Don't skip validation steps
- ✗ Don't rush quality for speed

---

## Example: Full Workflow

### Real Example: Adding "doctor" Command

**Step 1: Analysis (Claude)**
```markdown
# Analysis: Health Check Command

## Problem
Users can't easily diagnose setup issues.

## Proposed Solution
Add `qaagent doctor` command that checks:
- Python version
- Installed extras
- System dependencies (node, playwright)
- Ollama status
- MCP server startup

## Success Criteria
- [ ] One command shows all health status
- [ ] Color-coded output (green/yellow/red)
- [ ] Suggests fixes for issues found
- [ ] Takes < 5 seconds to run

## Questions for Codex
1. Should we check network connectivity?
2. How to handle slow checks (timeout)?
```

**Step 2: Review (Codex)**
```markdown
# Review: doctor Command

## Summary
Agree with approach. Implementation is straightforward.

## Answers
1. Network: Yes, but with 2s timeout
2. Slow checks: Run in parallel with asyncio

## Implementation Plan
- Add `doctor()` in cli.py
- Create checks.py for health logic
- Use rich Table for output
- Return exit code 1 if any red status

## Estimate
2-3 hours
```

**Step 3: Agreement**
Both: ✅ Ready to implement

**Step 4: Implementation (Codex)**
- Writes code
- Adds tests
- Updates README
- Creates example output

**Step 5: Review (Claude + User)**
- Claude reviews code ✅
- User tests on Mac M1 ✅
- Merged! 🎉

---

## Current Status

**Phase**: Developer Experience & Validation
**Active Document**: [docs/PHASE_1_ANALYSIS.md](PHASE_1_ANALYSIS.md)
**Status**: Awaiting Codex review
**Next**: Codex proposes implementation approach

---

**Last Updated**: 2025-10-22
