# Week 3 Plan: Real-World Integration & Enhancement

**Date**: 2025-10-23
**Goal**: Make QA Agent production-ready for SonicGrid and other real-world projects
**Duration**: 4 days
**Implementation**: Claude (Analysis Agent)

---

## Executive Summary

Week 3 focuses on **real-world usability** by adding Next.js route discovery, remote repository support, and quality-of-life improvements needed to test SonicGrid and similar production applications.

**Key Deliverables**:
1. **Next.js Route Discovery** - Auto-parse App Router routes from source code
2. **Remote Repository Support** - Clone and analyze repos from GitHub URLs
3. **Enhanced OpenAPI Generation** - Create specs from discovered routes
4. **Improved Test Generation** - Better assertions and realistic test data
5. **SonicGrid Integration** - Full end-to-end validation on real Next.js app

---

## Motivation

### Current Limitation

Week 2 requires **manual OpenAPI specs** for Next.js apps:
```bash
# Current workflow (Week 2)
cd ~/projects/sonic/sonicgrid
qaagent config init . --template nextjs
# ❌ Problem: Need to manually create openapi.yaml for Next.js routes
cp ~/sonicgrid-openapi.yaml .  # Manual step!
qaagent analyze routes --openapi openapi.yaml
```

### Week 3 Goal

**Automated route discovery** for Next.js:
```bash
# Week 3 workflow
cd ~/projects/sonic/sonicgrid
qaagent config init . --template nextjs --auto-discover
# ✅ Automatically discovers routes from src/app/api/*/route.ts
qaagent analyze routes  # No --openapi flag needed!
qaagent generate behave
qaagent generate unit-tests
```

**Or start from GitHub URL**:
```bash
# Week 3: Remote repos
qaagent config init https://github.com/spherop/sonicgrid --template nextjs --auto-discover
qaagent analyze routes
```

---

## Week 3 Roadmap

### Day 1: Next.js Route Discovery 🚀 **START HERE**

**Goal**: Auto-discover API routes from Next.js App Router source code

#### Tasks

1. **Create Route Discovery Module** (`src/qaagent/discovery/`)
   - `nextjs_parser.py` - Parse `route.ts` files with AST
   - `route_extractor.py` - Extract method handlers (GET, POST, etc.)
   - `types_analyzer.py` - Infer request/response types from TypeScript

2. **Implement Next.js Parser**
   ```python
   class NextJsRouteDiscoverer:
       def discover(self, project_root: Path) -> List[Route]:
           # Find all src/app/api/**/route.ts files
           # Parse each with esprima or ts-ast-parser
           # Extract GET, POST, PUT, DELETE, PATCH handlers
           # Infer path from directory structure
           # Return Route objects
   ```

3. **Integration Points**
   - Update `discover_routes()` to auto-detect Next.js projects
   - Use `.qaagent.yaml` flag: `openapi.auto_generate: true`
   - Fall back to manual OpenAPI if auto-discovery fails

4. **CLI Updates**
   - `qaagent config init` gets `--auto-discover` flag
   - `qaagent analyze routes` auto-detects source if no `--openapi` provided

5. **Testing**
   - Unit tests for AST parsing
   - Integration test with sample Next.js app
   - Test with SonicGrid structure

**Validation Criteria**:
- ✅ Can discover routes from `src/app/api/users/route.ts`
- ✅ Correctly identifies HTTP methods
- ✅ Infers paths from directory structure
- ✅ Handles dynamic routes like `[id]`
- ✅ Works on real SonicGrid codebase

**Dependencies**:
- `esprima` or `tree-sitter` for JavaScript/TypeScript AST parsing
- Pattern matching for Next.js App Router conventions

---

### Day 2: Remote Repository Support 🌐

**Goal**: Clone and analyze repositories from GitHub URLs

#### Tasks

1. **Create Repository Manager** (`src/qaagent/repo/`)
   - `cloner.py` - Clone repos with git
   - `cache.py` - Cache cloned repos in `~/.qaagent/repos/`
   - `validator.py` - Validate repo structure

2. **Implement Git Cloning**
   ```python
   class RepoCloner:
       def clone(self, url: str, target_name: str) -> Path:
           # Parse GitHub URL
           # Clone to ~/.qaagent/repos/<org>/<repo>
           # Return local path
           # Handle authentication for private repos
   ```

3. **Integration with Config System**
   - `qaagent config init <github-url>` clones repo first
   - Auto-detects project type (Next.js, FastAPI, etc.)
   - Creates `.qaagent.yaml` in cloned repo
   - Registers in targets list

4. **CLI Commands**
   - `qaagent repo clone <url> --name <target>`
   - `qaagent repo list` (show all cloned repos)
   - `qaagent repo update <name>` (git pull)
   - `qaagent repo remove <name>` (delete cached repo)

5. **Authentication Support**
   - Support HTTPS + token via env var
   - Support SSH keys
   - Respect .netrc for credentials

**Validation Criteria**:
- ✅ Can clone public GitHub repos
- ✅ Can clone private repos with auth
- ✅ Caches repos to avoid re-cloning
- ✅ Updates existing clones with `git pull`
- ✅ Works with SonicGrid repo

**Dependencies**:
- `gitpython` or subprocess `git` commands
- GitHub URL parsing

---

### Day 3: Enhanced OpenAPI & Test Generation 📝

**Goal**: Generate better OpenAPI specs and improve test quality

#### Tasks

1. **OpenAPI Generator from Routes**
   - `src/qaagent/openapi/generator.py`
   - Convert discovered Next.js routes to OpenAPI 3.0 spec
   - Infer request/response schemas from TypeScript types
   - Add proper tags, summaries, descriptions

2. **Improved Test Data in Generated Tests**
   - Update `UnitTestGenerator` to use `DataGenerator`
   - Replace empty `{}` in POST/PUT tests with realistic data
   - Use Faker-generated data for test requests

3. **Better Assertions**
   - Add response schema validation in generated tests
   - Check common fields (id, created_at, etc.)
   - Validate status codes more strictly

4. **Template Improvements**
   - Add setup/teardown in conftest.py
   - Add authentication helpers
   - Add common assertions library

**Example Enhanced Test**:
```python
def test_post_pets_success(self, api_client, sample_pet_data):
    """Test POST /pets creates a new pet"""
    response = api_client.post("/pets", json=sample_pet_data)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["name"] == sample_pet_data["name"]
    assert data["species"] in ["dog", "cat", "bird", "fish"]
```

**Validation Criteria**:
- ✅ Generates valid OpenAPI 3.0 from Next.js routes
- ✅ Generated tests use realistic data
- ✅ Tests validate response structure
- ✅ Better coverage of edge cases

---

### Day 4: SonicGrid Integration & Polish 🎯

**Goal**: Validate entire system on real SonicGrid project

#### Tasks

1. **SonicGrid Full Workflow Test**
   ```bash
   # Test complete workflow
   qaagent config init https://github.com/spherop/sonicgrid --auto-discover
   qaagent analyze routes
   qaagent analyze risks
   qaagent generate behave
   qaagent generate unit-tests
   qaagent generate test-data User --count 100
   ```

2. **Quality of Life Improvements**
   - Better error messages
   - Progress indicators for long operations
   - Colorized CLI output
   - `--verbose` flag for debugging

3. **Documentation**
   - Create `docs/SONICGRID_TUTORIAL.md`
   - Update README with Next.js examples
   - Document remote repo workflow
   - Add troubleshooting guide

4. **Create Week 3 Validation Report**
   - Test all new features
   - Validate SonicGrid integration
   - Performance benchmarks
   - Document any issues

**Validation Criteria**:
- ✅ Can analyze SonicGrid from GitHub URL
- ✅ Discovers all Next.js API routes
- ✅ Generates runnable tests for SonicGrid
- ✅ Complete documentation for users
- ✅ All tests passing

---

## Success Criteria

Week 3 is **COMPLETE** when:

### Core Features ✅

- [ ] **Next.js Route Discovery**
  - [ ] Discovers routes from `src/app/api/*/route.ts`
  - [ ] Handles dynamic routes `[param]`
  - [ ] Identifies HTTP methods correctly
  - [ ] Works on SonicGrid

- [ ] **Remote Repository Support**
  - [ ] Clones from GitHub URLs
  - [ ] Caches repos locally
  - [ ] Supports authentication
  - [ ] Updates with `git pull`

- [ ] **Enhanced OpenAPI Generation**
  - [ ] Generates valid OpenAPI 3.0 spec
  - [ ] Infers schemas from TypeScript
  - [ ] Proper tags and descriptions

- [ ] **Better Test Generation**
  - [ ] Uses realistic test data
  - [ ] Validates response structure
  - [ ] Better assertions

### SonicGrid Integration ✅

- [ ] Can initialize from GitHub URL
- [ ] Auto-discovers all routes
- [ ] Generates runnable tests
- [ ] Tests validate API behavior
- [ ] Documentation complete

### Testing ✅

- [ ] Unit tests for new components (>30 tests)
- [ ] Integration tests for workflows (>5 tests)
- [ ] Manual validation on SonicGrid
- [ ] All existing tests still pass

---

## Dependencies to Add

```toml
[project.optional-dependencies]
# For AST parsing
discovery = [
    "esprima>=4.0",       # JavaScript/TypeScript AST
    "tree-sitter>=0.20",  # Alternative parser
]

# For git operations
repo = [
    "gitpython>=3.1",     # Git operations
]

# Combined
all = [
    "qaagent[api,ui,mcp,llm,discovery,repo]"
]
```

---

## Architecture

### New Packages

```
src/qaagent/
├── discovery/          # NEW - Route discovery
│   ├── __init__.py
│   ├── nextjs_parser.py
│   ├── route_extractor.py
│   └── types_analyzer.py
├── repo/               # NEW - Repository management
│   ├── __init__.py
│   ├── cloner.py
│   ├── cache.py
│   └── validator.py
├── openapi/            # NEW - OpenAPI generation
│   ├── __init__.py
│   ├── generator.py
│   └── schema_inferrer.py
```

### Updated Modules

- `src/qaagent/analyzers/route_discovery.py` - Add Next.js auto-discovery
- `src/qaagent/config/loader.py` - Handle remote URLs
- `src/qaagent/generators/unit_test_generator.py` - Use DataGenerator
- `src/qaagent/cli.py` - Add new commands

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| TypeScript AST parsing complex | Medium | High | Use proven libraries (esprima), start simple |
| GitHub auth difficult | Low | Medium | Support multiple auth methods |
| SonicGrid has unexpected structure | Medium | High | Test early, iterate based on findings |
| Performance issues with large repos | Low | Medium | Implement caching, progress indicators |

### Mitigation Strategies

1. **Start Simple**: Parse basic Next.js routes first, add complexity later
2. **Early Testing**: Test on SonicGrid from Day 1 to catch issues early
3. **Fallback Options**: Keep manual OpenAPI option for edge cases
4. **Good Logging**: Verbose mode for debugging parsing issues

---

## Out of Scope (Future Weeks)

These are **NOT** in Week 3:

- ❌ LLM integration (Ollama) - Defer to Week 4+
- ❌ LangGraph orchestration - Defer to Week 4+
- ❌ RAG for context - Defer to Week 4+
- ❌ UI test generation - Defer to Week 5+
- ❌ FastAPI route auto-discovery - Focus on Next.js first
- ❌ GraphQL support - REST APIs only for now

---

## Expected Outcomes

### User Experience (Before Week 3)

```bash
# Manual process
cd ~/projects/sonic/sonicgrid
# Create OpenAPI spec manually 😞
vim openapi.yaml  # 200+ lines of YAML
qaagent config init . --template nextjs
qaagent analyze routes --openapi openapi.yaml
```

### User Experience (After Week 3)

```bash
# Automated process
qaagent config init https://github.com/spherop/sonicgrid --auto-discover
# ✨ Routes discovered automatically from source code!
qaagent analyze routes  # No manual spec needed
qaagent generate behave
qaagent generate unit-tests
behave tests/behave
pytest tests/unit
```

---

## Timeline

| Day | Focus | Key Deliverable |
|-----|-------|-----------------|
| Day 1 | Next.js Route Discovery | Parse route.ts files → Routes |
| Day 2 | Remote Repository Support | Clone GitHub → Local cache |
| Day 3 | Enhanced Generation | Routes → Better tests |
| Day 4 | SonicGrid Integration | Full validation on real app |

**Total**: 4 days
**Start**: Day 1 (Next.js Route Discovery)

---

## Questions to Resolve

Before starting Day 1:

1. **Next.js App Router Only?**
   - Decision: Yes, focus on App Router (`src/app/api/*/route.ts`)
   - Pages Router (`pages/api/`) can be added later

2. **TypeScript Type Inference?**
   - Decision: Basic type inference from function signatures
   - Complex types → fallback to generic schemas

3. **Authentication for Private Repos?**
   - Decision: Support `GITHUB_TOKEN` env var
   - SSH keys if time permits

4. **SonicGrid Structure Assumptions?**
   - Decision: Test early on actual SonicGrid to validate assumptions
   - Adjust parser based on real structure

---

## Ready to Start?

**Prerequisites**:
- ✅ Week 2 complete and validated
- ✅ All tests passing
- ✅ SonicGrid repository accessible
- ✅ Week 3 plan reviewed

**Recommended Order**:
1. Day 1: Next.js parser (foundation)
2. Test on SonicGrid early (validate approach)
3. Day 2: Remote repos (enables easier testing)
4. Day 3-4: Iterate based on real findings

---

**Let's build something amazing for Week 3!** 🚀

---

**Created by**: Claude (Analysis Agent)
**Date**: 2025-10-23
**Status**: Ready for Implementation
