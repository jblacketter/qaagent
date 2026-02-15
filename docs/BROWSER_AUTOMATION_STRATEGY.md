# Browser Automation Strategy: MCP Server vs CLI for AI-Driven QA

**Date:** 2026-02-10
**Source:** Field testing on [Northstar](https://github.com/jackblacketter/northstar-test-automation) QA environment
**Relevance:** Informs how qaagent should implement live browser inspection for UI route discovery, DOM auditing, and interactive test generation

---

## Context

qaagent currently generates Playwright TypeScript E2E tests from route metadata and runs them via `npx playwright test`. This is a **generate-then-run** workflow — the agent never sees the live DOM.

Adding **live browser inspection** would unlock:
- UI route discovery by crawling (Phase 2A goal)
- DOM structure analysis for selector strategy (data-testid, ARIA roles, CSS)
- Visual regression baseline capture
- Runtime state inspection for test data setup
- Interactive test recording and replay

Two approaches were evaluated for driving a browser from an AI agent context:

| | `@playwright/mcp` (MCP Server) | `playwright-cli` (CLI tool) |
|---|---|---|
| How it works | Native tool calls via Model Context Protocol | Shell commands via Bash |
| Snapshot delivery | Inline in every tool response | Written to `.yml` files, read on demand |

---

## Token Cost Comparison

**Test:** Log into Auth0-protected app, navigate to a form-heavy page (31 fields, 51-option dropdown), extract all `data-testid` attributes.

### Results

| Metric | MCP Server | playwright-cli | playwright-cli (no file read) |
|---|---|---|---|
| Tool calls | 6 | 8 | 7 |
| Input tokens | ~150 | ~150 | ~125 |
| **Output tokens** | **~2,925** | **~1,075** | **~675** |
| **Total tokens** | **~3,075** | **~1,225** | **~800** |
| **Cost ratio** | **2.5x – 3.8x** | 1x | 1x |

> Token estimates: ~4 characters = 1 token. Measured on a real Angular app with Auth0 login.

### Where MCP Overhead Comes From

| Source | % of MCP output | Why |
|---|---|---|
| Inline accessibility snapshots | ~60% | Full YAML tree returned on every `navigate`, `click`, `wait_for` — including all dropdown options, form fields, etc. No opt-out. |
| Console/event logs | ~15% | Auth tokens, Google Maps warnings, network events appended automatically |
| Snapshot metadata | ~25% | Element refs, roles, labels, cursor states for every DOM node |

### The Key Difference

**MCP** returns the full page accessibility tree inline with every action — whether you need it or not. A single snapshot of a form with a 51-state dropdown costs ~1,200 tokens.

**playwright-cli** writes snapshots to `.yml` files and returns only a file path (~10 tokens). You choose when to read the file content into context.

---

## Ergonomics Comparison

| Feature | MCP Server | playwright-cli |
|---|---|---|
| **Setup** | `claude mcp add playwright` | `npm i -g playwright-cli` |
| **Invocation** | Native tool calls (`browser_click ref=e28`) | Bash commands (`playwright-cli click e28`) |
| **Session management** | Automatic (MCP manages lifecycle) | Manual `open` / `close` |
| **Element refs** | Always available (inline snapshot) | Requires `snapshot` → `Read` file → find ref |
| **Multi-field forms** | `fill_form` fills multiple fields at once | One `fill <ref> <value>` per field |
| **JS evaluation** | Clean — pass function, get structured JSON | Quirky — `map()` fails, `reduce()` works, multi-statement needs workarounds |
| **Parallel usage** | One browser per MCP server instance | Multiple named sessions supported |

---

## Recommendations for qaagent

### 1. Use playwright-cli (or equivalent) for Automated Pipelines

When qaagent runs `analyze routes --crawl` or `analyze dom --url`, it should minimize token overhead:

```
Route: qaagent CLI → spawn headless browser → targeted JS eval → structured JSON → close
```

- Don't load full accessibility trees into LLM context unless explicitly needed
- Use `page.evaluate()` with targeted queries (e.g., `querySelectorAll('[data-testid]')`)
- Return structured data (JSON), not raw DOM trees
- This maps to the existing `playwright_runner.py` pattern of spawning subprocesses

### 2. Consider MCP for Interactive/Agent Mode

If qaagent adds an interactive mode where an AI agent explores a UI step-by-step:

```
Route: LLM agent → MCP tool calls → snapshot → decide next action → click/fill → repeat
```

MCP's inline snapshots are valuable here because the agent needs refs to decide what to click. But:
- **Budget for 2-4x token cost** vs CLI approach
- **Complex pages are expensive** — forms with dropdowns, tables, modals
- Consider a **snapshot budget** — skip snapshots on known navigation steps, only snapshot when the agent needs to make a decision

### 3. Hybrid Strategy (Recommended)

| Use Case | Approach | Reason |
|---|---|---|
| Route discovery / crawling | Direct Playwright (subprocess) | Cheapest, most controlled |
| DOM auditing (`data-testid`, ARIA) | playwright-cli `eval` | Targeted queries, minimal tokens |
| Selector strategy analysis | playwright-cli `snapshot` + file read | Full DOM when needed, on demand |
| Interactive exploration | MCP Server | Agent needs inline refs for decisions |
| Test generation from live DOM | playwright-cli `eval` → feed results to LLM | Structured data in, test code out |
| Visual regression | Direct Playwright (screenshot API) | No LLM tokens needed |

### 4. Implementation Roadmap Items

#### Near-term: DOM Inspector Command
```bash
qaagent analyze dom --url https://app.example.com/dashboard --auth-config .qaagent.yaml
```
- Uses headless Playwright (subprocess, not MCP)
- Extracts: element inventory, selector coverage (data-testid, ARIA, CSS), form structure, navigation links
- Outputs: `dom-analysis.json` with selector recommendations
- Token cost: near-zero (no LLM until report generation)

#### Mid-term: Live UI Route Discovery
```bash
qaagent analyze routes --crawl --url https://app.example.com --depth 3
```
- Crawls app via Playwright, following links and navigation
- Discovers UI routes not in OpenAPI spec
- Captures page structure at each route
- Feeds into existing risk assessment and test generation pipelines

#### Future: AI-Assisted Test Recording
```bash
qaagent record --url https://app.example.com --goal "test checkout flow"
```
- LLM-driven browser exploration (MCP or agent loop)
- Agent decides what to click/fill based on goal
- Records actions as Behave scenarios or Playwright TypeScript
- Token budget management built in (snapshot throttling, targeted evals)

---

## Technical Notes

### Auth Handling
- Auth0 (and similar OAuth flows) work with both approaches
- Pattern: navigate to protected URL → detect redirect to login → fill credentials → submit → follow redirect back
- qaagent's existing `auth.setup.ts.j2` template handles this for generated tests
- For live inspection, the auth flow needs to be replayed in the browser session

### Complex Pages (Worst Case for MCP)
Pages with these features inflate MCP snapshots significantly:
- Large `<select>` dropdowns (51 states = ~500 extra tokens per snapshot)
- Data tables with many rows
- Nested modals/dialogs
- Rich text editors
- Google Maps or other embedded widgets

qaagent should detect these and prefer targeted `eval` over full snapshots.

### Snapshot File Format
playwright-cli writes YAML accessibility trees to `.playwright-cli/page-{timestamp}.yml`. These are the same format as MCP inline snapshots but stored on disk. qaagent could:
- Parse these files for element inventory
- Diff snapshots between page loads for change detection
- Archive snapshots as test evidence

---

## References

- [Full comparison report](../northstar-test-automation/docs/mcp-vs-playwright-cli-comparison.md) (Northstar project)
- [@playwright/mcp](https://github.com/anthropics/playwright-mcp) — Official MCP server
- [playwright-cli](https://www.npmjs.com/package/playwright-cli) — CLI wrapper for Playwright MCP operations
- qaagent Playwright runner: `src/qaagent/runners/playwright_runner.py`
- qaagent Playwright generator: `src/qaagent/generators/playwright_generator.py`
