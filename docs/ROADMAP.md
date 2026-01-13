# QA Agent - Feature Roadmap

## ✅ Completed (Sprint 3)

### Sprint 1-2: Foundation
- [x] Evidence collection pipeline (collectors, analyzers, risk aggregation)
- [x] FastAPI-based REST API (repository and run management)
- [x] React dashboard (repository-centric workflow, dark mode)
- [x] Risk prioritization with severity grouping
- [x] Comprehensive test coverage

### Sprint 3: Auto-Fix & Enhanced Scanning
- [x] Fixed Bandit timeout issue (increased to 10min, smart filtering)
- [x] `qaagent fix` command (autopep8, black, isort integration)
- [x] Enhanced recommendations with actionable commands
- [x] Auto-fix for formatting and import issues
- [x] Documentation: AUTO_FIX_GUIDE.md

## 📋 Planned Features

### Next Sprint: LLM-Powered Fixes
**Priority:** High
**Estimated Time:** 3.5 hours
**Prerequisites:** Ollama on Windows GPU machine

**Features:**
- [ ] LLM client module (Ollama integration)
- [ ] AI-powered fix generator
- [ ] `qaagent fix-llm` CLI command
- [ ] Context-aware security fixes
- [ ] Fix explanations (what changed and why)
- [ ] Confidence scoring

**Documentation:** LLM_POWERED_FIXES.md (created)

**Setup Required:**
- Configure Ollama on Windows for network access
- Pull DeepSeek Coder or CodeLlama model
- Test Mac → Windows connectivity

### Future: Enhanced Security Scanning
**Priority:** Medium-High
**Estimated Time:** 1-2 hours

**Features:**
1. **Secrets Detection** (30 min)
   - Find hardcoded API keys, passwords, tokens
   - Integration with `detect-secrets` or `trufflehog`
   - Auto-detect common patterns (AWS keys, GitHub tokens, etc.)

2. **JavaScript/Node.js Security** (30 min)
   - `npm audit` integration
   - `yarn audit` integration
   - Detect vulnerable dependencies in package.json

**Benefits:**
- Find security issues earlier
- Reduce false positives (bandit-only misses JS vulnerabilities)
- Better coverage for Next.js projects like SonicGrid

### Future: Dashboard Enhancements
**Priority:** Medium
**Estimated Time:** 2-3 hours

**Features:**
- [ ] Fix tracking between scans (show what was fixed)
- [ ] Improvement score over time
- [ ] "What changed" reports (before/after comparison)
- [ ] Export reports to PDF/Markdown
- [ ] Share reports via URL

### Future: Test Generation
**Priority:** Low-Medium
**Estimated Time:** 3-4 hours

**Features:**
- [ ] LLM-generated test cases for untested code
- [ ] Property-based tests for critical functions
- [ ] Integration test templates
- [ ] Test coverage goals

### Future: CI/CD Integration
**Priority:** Low
**Estimated Time:** 2 hours

**Features:**
- [ ] GitHub Actions workflow template
- [ ] GitLab CI template
- [ ] Pre-commit hooks for auto-fix
- [ ] PR commenting with fix suggestions

## 🚫 Deferred Features

### Auto-create PRs (Removed from roadmap)
**Reason:** Too complex for current needs
**Alternative:** Focus on generating fixes that developers can review and apply manually

## Implementation Priority

### Immediate (This Sprint)
1. None - Sprint 3 completed!

### Next Sprint (When on Windows)
1. **LLM-Powered Fixes** - High value, enables AI-assisted fixing

### After LLM Integration
1. **Secrets Detection** - Quick win, high security value
2. **npm/yarn Audit** - Completes JS security coverage

### Future Sprints
1. Dashboard enhancements (tracking, comparisons)
2. Test generation with LLM
3. CI/CD integration templates

## Success Metrics

### Sprint 3 (Completed)
- ✅ Bandit completes on large projects (no timeout)
- ✅ Users can auto-fix formatting in one command
- ✅ Recommendations include actionable commands
- ✅ Documentation covers all new features

### Next Sprint (LLM Fixes)
- LLM generates fixes with >70% confidence
- Fixes are accurate and applicable
- Response time <30 seconds per fix
- Windows ↔ Mac communication is stable

### Future Sprints
- Reduce false positives by 50%
- Increase code coverage detection
- Faster scan times (<5 min for large projects)

## Technical Debt

### Current
- Bundle size optimization for React dashboard (197 KB gzipped)
  - Use code splitting (lazy loading routes)
  - Split vendor chunks

### Future
- Add unit tests for auto-fix module
- Add integration tests for LLM client
- Improve error handling in collectors

## Dependencies

### Installed
- flake8, pylint, bandit, pip-audit (Python quality/security)
- isort (import sorting)
- FastAPI, uvicorn (API server)
- React, TypeScript (dashboard)

### Need to Install
- **For LLM Fixes:**
  - None (uses remote Ollama server)

- **For Secrets Detection:**
  - `detect-secrets` or `trufflehog`

- **For JS Scanning:**
  - None (uses existing npm/yarn)

- **For Auto-fix:**
  - `autopep8` (recommended for users)
  - `black` (optional alternative)

## Notes

- All features should include documentation
- Breaking changes require migration guide
- Security features take priority over convenience
- Performance: scan time should stay <10 min for 100k LOC projects

## Questions / Decisions Needed

1. **LLM Model Choice:** DeepSeek Coder 6.7B vs CodeLlama 13B?
   - Recommend: DeepSeek Coder (better for Python/JS)

2. **Secrets Detection Tool:** detect-secrets vs trufflehog?
   - TBD when implementing

3. **Auto-apply LLM Fixes:** Allow with flag or always manual review?
   - Decision: Always manual review for safety

## Resources

- **Documentation:** `docs/`
- **Examples:** `examples/`
- **Tests:** `tests/`
- **Discussions:** GitHub Issues

---

**Last Updated:** 2025-10-27
**Next Review:** After LLM integration sprint
