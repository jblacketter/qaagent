# Decision Log

This log tracks important decisions made during the project.

<!-- Add new decisions at the top in reverse chronological order -->

---

## 2026-02-07: Reset Roadmap from Sprint-Based to Phase-Based

**Decision:** Replace the old sprint-based roadmap (Oct 2025) with a 4-phase plan: Modernization → Test Framework Gen → Orchestration → Enhanced Analysis.

**Context:** The project has been dormant since Oct 2025. The old roadmap focused on incremental sprint features (LLM fixes, secrets detection, dashboard enhancements). The user's key priority has shifted to generating actual test frameworks from QA analysis, which requires a more ambitious restructuring.

**Alternatives Considered:**
- Continue sprint-based roadmap: Low risk, but doesn't address the test framework generation gap
- Jump straight to test framework gen: Faster to value, but builds on a fragile foundation (monolithic CLI, Ollama-only LLM)
- Full rewrite: Too risky, loses working functionality

**Rationale:** Phase-based approach balances debt payoff (Phase 1) with feature velocity (Phase 2). Modernization enables better test gen, and both phases are well-scoped.

**Decided By:** claude (Lead) - pending reviewer approval

**Phase:** roadmap (cross-cutting)

**Follow-ups:**
- Codex reviews Phase 1 + Phase 2 plans
- Human approves overall direction

---

## 2026-02-07: Multi-Provider LLM Over Ollama-Only

**Decision:** Expand LLM support from Ollama-only to Anthropic (Claude) + OpenAI + Ollama, with provider selection via `QAAGENT_LLM` env var and `.qaagent.yaml` config.

**Context:** The current llm.py only supports Ollama (local model). Phase 2's test framework generation engine needs high-quality code generation, which benefits from Claude/GPT-4 class models. Local Ollama models are not reliably good enough for generating runnable test code.

**Alternatives Considered:**
- Keep Ollama-only: Simple, no API costs, but output quality insufficient for code gen
- Use litellm as abstraction: Convenient, but adds a heavy dependency
- Hand-roll provider adapters: More control, fewer deps, but more code

**Rationale:** Start with hand-rolled adapters (they're simple: each is ~20 lines), flag litellm as open question for reviewer.

**Decided By:** claude (Lead) - pending reviewer approval

**Phase:** modernization

**Follow-ups:**
- Add `anthropic` to `[llm]` extras in pyproject.toml
- Refactor `llm.py` to `LLMClient` class with provider adapters
