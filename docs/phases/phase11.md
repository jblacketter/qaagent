# Phase 11: New Language Parsers

## Status
- [x] Planning
- [x] Implementation
- [x] Complete

## Roles
- Lead: codex
- Reviewer: skipped (direct execution approved by user)

## Summary
**What:** Extend source route discovery to non-Python frameworks in Go, Ruby, and Rust.
**Why:** Route analysis and downstream QA planning should work for mixed-language repositories, not only Python/Next.js targets.
**Depends on:** Phase 10 (RAG-Powered Test Generation) - Complete

## Scope

### In Scope
- Add framework parsers for:
  - Go: net/http, Gin, Echo
  - Ruby: Rails routes, Sinatra
  - Rust: Actix Web, Axum
- Register parsers in discovery registry and wire auto-detection in source discovery flow.
- Extend repository/project detection for Go/Ruby/Rust in validator and config detection.
- Add fixtures and tests for parser output, route normalization compatibility, and auto-detection.

### Out of Scope
- Deep semantic AST parsing for all language edge cases.
- Runtime crawling for these frameworks.
- OpenAPI generation enhancements specific to new language metadata.

## Technical Approach
- Keep V1 dependency-light by using deterministic regex/line parsing plus balanced-parentheses scanning (Rust router calls).
- Reuse existing `FrameworkParser` normalization contract so output remains compatible with:
  - risk assessment
  - OpenAPI generation
  - route coverage mapping
- Preserve deterministic ordering by scanning files in sorted order.

## Files Added
- `src/qaagent/discovery/go_parser.py`
- `src/qaagent/discovery/ruby_parser.py`
- `src/qaagent/discovery/rust_parser.py`
- `tests/fixtures/discovery/go_project/main.go`
- `tests/fixtures/discovery/ruby_project/config/routes.rb`
- `tests/fixtures/discovery/ruby_project/app.rb`
- `tests/fixtures/discovery/rust_project/Cargo.toml`
- `tests/fixtures/discovery/rust_project/src/main.rs`
- `tests/unit/discovery/test_go_parser.py`
- `tests/unit/discovery/test_ruby_parser.py`
- `tests/unit/discovery/test_rust_parser.py`

## Files Modified
- `src/qaagent/discovery/__init__.py`
- `src/qaagent/analyzers/route_discovery.py`
- `src/qaagent/repo/validator.py`
- `src/qaagent/config/detect.py`
- `tests/unit/analyzers/test_route_discovery.py`
- `tests/unit/repo/test_validator.py`
- `tests/unit/config/test_detect.py`

## Success Criteria
- [x] Go routes discovered from net/http, Gin, and Echo patterns
- [x] Ruby routes discovered from Rails DSL and Sinatra handlers
- [x] Rust routes discovered from Actix macros/web routes and Axum router patterns
- [x] Auto-detection selects appropriate parser for Go/Ruby/Rust repositories
- [x] Route output remains compatible with existing consumer expectations (`params` shape, normalized path forms)
- [x] Unit/integration coverage added for parsers and detection layers

## Risks
- Regex-driven parsing may miss uncommon DSL forms. Mitigation: fixture-backed coverage for common patterns and clear metadata confidence.
- Cross-language false positives in detection. Mitigation: require framework markers and route-pattern checks in validator heuristics.
