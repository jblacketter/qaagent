# Sprint 2 Plan: Risk Aggregation & API Layer

**Created**: 2025-10-24
**Owner**: Codex (implementation) + Claude (checkpoints)
**Status**: Ready to start
**Depends on**: Sprint 1 (Evidence Layer) ✅ COMPLETE

---

## Overview

Sprint 2 builds on Sprint 1's evidence collection to compute actionable insights:
- **Risk Aggregation**: Read evidence, apply weights, generate risk scores
- **Coverage-to-CUJ Mapping**: Map coverage to critical user journeys
- **API Layer**: Serve evidence and analysis via REST endpoints
- **Recommendation Engine**: Suggest testing priorities

---

## Sprint Goals

By the end of Sprint 2, users should be able to:
1. Run `qaagent analyze collectors` (Sprint 1) to gather evidence
2. Run `qaagent analyze risks` to compute risk scores from evidence
3. Query `http://localhost:8000/api/runs` to browse analysis runs
4. Query `http://localhost:8000/api/runs/{run_id}/risks` to get top risks
5. See coverage mapped to CUJs with gap identification

---

## Architecture Context

### What We Have (Sprint 1)
```
~/.qaagent/runs/20251024_193012Z/
  manifest.json
  evidence/
    quality.jsonl      # Findings from flake8, pylint, bandit, pip-audit
    coverage.jsonl     # Coverage records
    churn.jsonl        # Git churn records
  artifacts/
    *.json, *.log      # Raw tool outputs
```

### What We're Building (Sprint 2)
```
~/.qaagent/runs/20251024_193012Z/
  manifest.json
  evidence/
    quality.jsonl
    coverage.jsonl
    churn.jsonl
    risks.jsonl        # ← NEW: Computed risk scores
    recommendations.jsonl  # ← NEW: Testing recommendations

src/qaagent/
  analyzers/
    risk_aggregator.py   # ← NEW: Risk scoring logic
    coverage_mapper.py   # ← NEW: CUJ coverage analysis
    recommender.py       # ← NEW: Recommendation engine
  api/
    server.py            # ← NEW: FastAPI application
    routes/
      runs.py            # ← NEW: /api/runs endpoints
      evidence.py        # ← NEW: /api/runs/{id}/evidence endpoints
      risks.py           # ← NEW: /api/runs/{id}/risks endpoints
```

---

## Task Breakdown

### Phase 1: Evidence Readers (Foundation)

#### S2-01: Evidence Reader Utilities
**Goal**: Create utilities to read JSONL evidence files

**Files to create**:
- `src/qaagent/analyzers/evidence_reader.py`

**Implementation**:
```python
class EvidenceReader:
    """Read and parse JSONL evidence files."""

    def __init__(self, run_handle: RunHandle):
        self.run_handle = run_handle

    def read_findings(self) -> List[FindingRecord]:
        """Read all findings from quality.jsonl."""

    def read_coverage(self) -> List[CoverageRecord]:
        """Read coverage records from coverage.jsonl."""

    def read_churn(self) -> List[ChurnRecord]:
        """Read churn records from churn.jsonl."""

    def read_manifest(self) -> Manifest:
        """Read and parse manifest.json."""
```

**Acceptance Criteria**:
- [ ] Can read quality.jsonl and parse into FindingRecord objects
- [ ] Can read coverage.jsonl and parse into CoverageRecord objects
- [ ] Can read churn.jsonl and parse into ChurnRecord objects
- [ ] Handles missing files gracefully (returns empty list, logs diagnostic)
- [ ] Unit tests with fixtures from Sprint 1 synthetic repo

**Estimated Complexity**: Low (1-2 hours)

---

### Phase 2: Risk Aggregation

#### S2-02: Risk Scoring Models
**Goal**: Define data models for risk records

**Files to create**:
- Add to `src/qaagent/evidence/models.py`

**Implementation**:
```python
@dataclass
class RiskRecord:
    risk_id: str                    # RSK-20251024-0001
    component: str                  # File path or CUJ ID
    score: float                    # 0-100
    band: str                       # P0, P1, P2, P3
    confidence: float               # 0.0-1.0
    severity: str                   # critical, high, medium, low
    title: str                      # Human-readable summary
    description: str                # Detailed explanation
    evidence_refs: List[str]        # List of evidence IDs contributing to risk
    factors: Dict[str, float]       # Breakdown: {"security": 45, "churn": 20, ...}
    recommendations: List[str]      # Action items
    created_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSONL."""
```

**Acceptance Criteria**:
- [ ] RiskRecord dataclass with all required fields
- [ ] to_dict() serialization
- [ ] Validation in __post_init__ (score 0-100, confidence 0-1)
- [ ] Unit tests for serialization

**Estimated Complexity**: Low (1 hour)

---

#### S2-03: Risk Configuration Loader
**Goal**: Load and parse risk_config.yaml

**Files to create**:
- `src/qaagent/analyzers/risk_config.py`

**Implementation**:
```python
@dataclass
class RiskWeights:
    security: float = 3.0
    coverage: float = 2.0
    churn: float = 2.0
    complexity: float = 1.5
    api_exposure: float = 1.0
    a11y: float = 0.5
    performance: float = 1.0

@dataclass
class RiskBand:
    name: str
    min_score: float

@dataclass
class RiskConfig:
    weights: RiskWeights
    bands: List[RiskBand]
    max_total: float = 100.0

    @staticmethod
    def load(path: Path) -> RiskConfig:
        """Load from risk_config.yaml."""
```

**Acceptance Criteria**:
- [ ] Loads handoff/risk_config.yaml successfully
- [ ] Parses weights, bands, caps
- [ ] Defaults to sensible values if file missing
- [ ] Unit tests with fixture YAML

**Estimated Complexity**: Low (1 hour)

---

#### S2-04: Risk Aggregator Core
**Goal**: Compute risk scores from evidence

**Files to create**:
- `src/qaagent/analyzers/risk_aggregator.py`

**Implementation**:
```python
class RiskAggregator:
    """Aggregate evidence into risk scores."""

    def __init__(self, config: RiskConfig):
        self.config = config

    def analyze(
        self,
        handle: RunHandle,
        reader: EvidenceReader,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> List[RiskRecord]:
        """
        Compute risks from evidence.

        Algorithm:
        1. Group findings by file path
        2. For each file:
           a. Compute security score (count critical/high findings * weight)
           b. Compute coverage score (1 - coverage_value) * weight
           c. Compute churn score (normalize commits/lines changed) * weight
           d. Sum weighted scores
           e. Normalize to 0-100
           f. Assign band (P0/P1/P2/P3)
           g. Compute confidence based on evidence density
        3. Write to risks.jsonl
        4. Return sorted by score descending
        """
        findings = reader.read_findings()
        coverage = reader.read_coverage()
        churn = reader.read_churn()

        # Group by component (file path)
        component_risks = self._compute_component_risks(findings, coverage, churn)

        # Create risk records
        risks = []
        for component, factors in component_risks.items():
            risk = self._create_risk_record(component, factors, id_generator)
            risks.append(risk)

        # Write to evidence store
        if risks:
            writer.write_records("risks", [r.to_dict() for r in risks])

        return sorted(risks, key=lambda r: r.score, reverse=True)

    def _compute_component_risks(
        self, findings, coverage, churn
    ) -> Dict[str, Dict[str, float]]:
        """Compute factor scores per component."""

    def _create_risk_record(
        self, component: str, factors: Dict[str, float], id_gen: EvidenceIDGenerator
    ) -> RiskRecord:
        """Create risk record from factors."""
        total_score = sum(factors.values())
        normalized = min(total_score, self.config.max_total)
        band = self._assign_band(normalized)
        confidence = self._compute_confidence(factors)

        return RiskRecord(
            risk_id=id_gen.next_id("rsk"),
            component=component,
            score=normalized,
            band=band,
            confidence=confidence,
            severity=self._score_to_severity(normalized),
            title=f"Risk in {component}",
            description=self._generate_description(factors),
            evidence_refs=[],  # TODO: Track which evidence IDs contributed
            factors=factors,
            recommendations=self._generate_recommendations(component, factors),
        )

    def _assign_band(self, score: float) -> str:
        """Assign P0/P1/P2/P3 based on thresholds."""
        for band in self.config.bands:
            if score >= band.min_score:
                return band.name
        return "P3"

    def _compute_confidence(self, factors: Dict[str, float]) -> float:
        """
        Confidence based on evidence diversity.
        More factor types with data = higher confidence.
        """
        present_factors = sum(1 for v in factors.values() if v > 0)
        total_factors = len(factors)
        return present_factors / total_factors if total_factors > 0 else 0.0
```

**Acceptance Criteria**:
- [ ] Reads findings, coverage, churn from evidence store
- [ ] Groups by component (file path)
- [ ] Computes weighted scores using risk_config.yaml
- [ ] Normalizes to 0-100
- [ ] Assigns band (P0/P1/P2/P3)
- [ ] Computes confidence (0-1) based on evidence density
- [ ] Writes risks.jsonl
- [ ] Returns sorted list (highest risk first)
- [ ] Unit tests with synthetic evidence
- [ ] Integration test with Sprint 1 synthetic repo

**Estimated Complexity**: Medium-High (4-6 hours)

**Notes**:
- Start simple: just file-level risks
- Future: CUJ-level risks (Sprint 3)
- Future: API endpoint risks (Sprint 3)

---

### Phase 3: Coverage-to-CUJ Mapping

#### S2-05: CUJ Configuration Loader
**Goal**: Load and parse cuj.yaml

**Files to create**:
- `src/qaagent/analyzers/cuj_config.py`

**Implementation**:
```python
@dataclass
class CUJEndpoint:
    method: str
    endpoint: str

@dataclass
class CriticalUserJourney:
    id: str
    name: str
    components: List[str]           # Glob patterns like "src/auth/*"
    apis: List[CUJEndpoint]
    acceptance: List[str]
    coverage_target: float = 70.0  # Default if not in coverage_targets

@dataclass
class CUJConfig:
    product: str
    journeys: List[CriticalUserJourney]

    @staticmethod
    def load(path: Path) -> CUJConfig:
        """Load from cuj.yaml."""

    def find_journey(self, cuj_id: str) -> Optional[CriticalUserJourney]:
        """Find journey by ID."""
```

**Acceptance Criteria**:
- [ ] Loads handoff/cuj.yaml successfully
- [ ] Parses journeys with components, apis, acceptance criteria
- [ ] Reads coverage_targets map
- [ ] Defaults to 70% if target not specified
- [ ] Unit tests with fixture YAML

**Estimated Complexity**: Low (1-2 hours)

---

#### S2-06: Coverage Mapper
**Goal**: Map coverage records to CUJs

**Files to create**:
- `src/qaagent/analyzers/coverage_mapper.py`

**Implementation**:
```python
@dataclass
class CUJCoverageResult:
    cuj_id: str
    cuj_name: str
    coverage: float              # Actual coverage percentage
    target: float                # Target from cuj.yaml
    gap: float                   # target - coverage (positive = gap)
    status: str                  # "pass", "warn", "fail"
    covered_files: List[str]
    missing_files: List[str]

class CoverageMapper:
    """Map coverage records to critical user journeys."""

    def __init__(self, cuj_config: CUJConfig):
        self.cuj_config = cuj_config

    def analyze(
        self,
        coverage_records: List[CoverageRecord],
    ) -> List[CUJCoverageResult]:
        """
        Map coverage to CUJs.

        Algorithm:
        1. For each CUJ:
           a. Match component patterns (glob) to coverage records
           b. Compute average coverage across matched files
           c. Compare to target
           d. Identify missing files (components not in coverage)
        2. Return results sorted by gap (largest gaps first)
        """
        results = []
        for journey in self.cuj_config.journeys:
            result = self._map_journey(journey, coverage_records)
            results.append(result)
        return sorted(results, key=lambda r: r.gap, reverse=True)

    def _map_journey(
        self, journey: CriticalUserJourney, records: List[CoverageRecord]
    ) -> CUJCoverageResult:
        """Map a single journey."""
        matched_records = self._match_components(journey.components, records)

        if not matched_records:
            coverage = 0.0
            covered_files = []
        else:
            coverage = sum(r.value for r in matched_records) / len(matched_records)
            covered_files = [r.component for r in matched_records]

        gap = journey.coverage_target - coverage
        status = "pass" if coverage >= journey.coverage_target else "fail"

        return CUJCoverageResult(
            cuj_id=journey.id,
            cuj_name=journey.name,
            coverage=coverage,
            target=journey.coverage_target,
            gap=gap,
            status=status,
            covered_files=covered_files,
            missing_files=[],  # TODO: Identify expected files not in coverage
        )

    def _match_components(
        self, patterns: List[str], records: List[CoverageRecord]
    ) -> List[CoverageRecord]:
        """Match glob patterns to coverage records."""
        import fnmatch
        matched = []
        for record in records:
            for pattern in patterns:
                if fnmatch.fnmatch(record.component, pattern):
                    matched.append(record)
                    break
        return matched
```

**Acceptance Criteria**:
- [ ] Loads CUJ config
- [ ] Matches component glob patterns to coverage records
- [ ] Computes average coverage per CUJ
- [ ] Identifies coverage gaps (target - actual)
- [ ] Returns sorted by gap (largest first)
- [ ] Unit tests with synthetic coverage data
- [ ] Integration test with Sprint 1 synthetic repo + cuj.yaml

**Estimated Complexity**: Medium (3-4 hours)

---

### Phase 4: Recommendation Engine

#### S2-07: Recommendation Generator
**Goal**: Generate actionable testing recommendations

**Files to create**:
- `src/qaagent/analyzers/recommender.py`

**Implementation**:
```python
@dataclass
class Recommendation:
    recommendation_id: str         # REC-20251024-0001
    priority: str                  # P0, P1, P2, P3
    category: str                  # "coverage", "security", "churn"
    title: str                     # "Add integration tests for auth login"
    description: str               # Detailed explanation
    rationale: str                 # Why this is important
    evidence_refs: List[str]       # Related evidence IDs
    cuj_id: Optional[str] = None   # Related CUJ if applicable
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSONL."""

class RecommendationEngine:
    """Generate testing recommendations from risks and coverage gaps."""

    def analyze(
        self,
        risks: List[RiskRecord],
        cuj_coverage: List[CUJCoverageResult],
        id_generator: EvidenceIDGenerator,
    ) -> List[Recommendation]:
        """
        Generate recommendations.

        Rules:
        1. High-risk (P0/P1) + low coverage → "Add tests for {component}"
        2. High churn + low coverage → "Stabilize tests for {component}"
        3. Security findings + public API → "Security review for {endpoint}"
        4. CUJ below target → "Increase coverage for {cuj_name}"
        """
        recommendations = []

        # Rule 1: High risk + low coverage
        for risk in risks:
            if risk.band in ("P0", "P1") and risk.factors.get("coverage", 0) > 20:
                rec = self._create_recommendation(
                    priority=risk.band,
                    category="coverage",
                    title=f"Add tests for {risk.component}",
                    description=f"High-risk component with low coverage. Score: {risk.score}",
                    rationale=f"Risk factors: {risk.factors}",
                    evidence_refs=[risk.risk_id],
                    id_gen=id_generator,
                )
                recommendations.append(rec)

        # Rule 2: CUJ coverage gaps
        for cuj in cuj_coverage:
            if cuj.status == "fail":
                rec = self._create_recommendation(
                    priority="P1" if cuj.gap > 20 else "P2",
                    category="coverage",
                    title=f"Increase coverage for {cuj.cuj_name}",
                    description=f"Current: {cuj.coverage:.1f}%, Target: {cuj.target:.1f}%, Gap: {cuj.gap:.1f}%",
                    rationale=f"Critical user journey below coverage target",
                    evidence_refs=[],
                    cuj_id=cuj.cuj_id,
                    id_gen=id_generator,
                )
                recommendations.append(rec)

        return sorted(recommendations, key=lambda r: r.priority)
```

**Acceptance Criteria**:
- [ ] Generates recommendations from high risks
- [ ] Generates recommendations from CUJ coverage gaps
- [ ] Prioritizes by severity (P0 > P1 > P2)
- [ ] Provides actionable titles and descriptions
- [ ] Unit tests with synthetic risks and coverage
- [ ] Integration test validates sensible recommendations

**Estimated Complexity**: Medium (2-3 hours)

---

### Phase 5: API Layer

#### S2-08: FastAPI Server Setup
**Goal**: Create basic FastAPI application

**Files to create**:
- `src/qaagent/api/__init__.py`
- `src/qaagent/api/server.py`

**Implementation**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="QA Agent API",
    description="Read-only API for QA Agent evidence store",
    version="1.0.0-mvp",
)

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure per environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "QA Agent API", "version": "1.0.0-mvp"}

@app.get("/health")
def health():
    return {"status": "healthy"}
```

**Acceptance Criteria**:
- [ ] FastAPI app with CORS enabled
- [ ] Root endpoint returns API info
- [ ] Health endpoint for monitoring
- [ ] Can run with `uvicorn qaagent.api.server:app`

**Estimated Complexity**: Low (30 minutes)

---

#### S2-09: Runs Endpoints
**Goal**: List and retrieve analysis runs

**Files to create**:
- `src/qaagent/api/routes/runs.py`

**Implementation**:
```python
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List
import json

router = APIRouter(prefix="/api/runs", tags=["runs"])

@router.get("/")
def list_runs() -> List[dict]:
    """List all analysis runs."""
    runs_dir = Path.home() / ".qaagent" / "runs"
    if not runs_dir.exists():
        return []

    runs = []
    for run_path in sorted(runs_dir.iterdir(), reverse=True):
        if not run_path.is_dir():
            continue
        manifest_path = run_path / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            runs.append({
                "run_id": run_path.name,
                "target": manifest.get("target", {}).get("path"),
                "created_at": manifest.get("created_at"),
                "counts": manifest.get("counts", {}),
            })
    return runs

@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    """Get run details including manifest."""
    run_path = Path.home() / ".qaagent" / "runs" / run_id
    manifest_path = run_path / "manifest.json"

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    manifest = json.loads(manifest_path.read_text())
    return manifest
```

**Acceptance Criteria**:
- [ ] GET /api/runs returns list of all runs
- [ ] GET /api/runs/{run_id} returns manifest
- [ ] Returns 404 if run not found
- [ ] Sorted by created_at descending

**Estimated Complexity**: Low (1 hour)

---

#### S2-10: Evidence Endpoints
**Goal**: Retrieve evidence from runs

**Files to create**:
- `src/qaagent/api/routes/evidence.py`

**Implementation**:
```python
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List
import json

router = APIRouter(prefix="/api/runs/{run_id}", tags=["evidence"])

@router.get("/findings")
def get_findings(run_id: str) -> List[dict]:
    """Get all findings from quality.jsonl."""
    evidence_file = Path.home() / ".qaagent" / "runs" / run_id / "evidence" / "quality.jsonl"

    if not evidence_file.exists():
        return []

    findings = []
    for line in evidence_file.read_text().strip().splitlines():
        if line:
            findings.append(json.loads(line))

    return findings

@router.get("/coverage")
def get_coverage(run_id: str) -> List[dict]:
    """Get coverage records."""
    evidence_file = Path.home() / ".qaagent" / "runs" / run_id / "evidence" / "coverage.jsonl"

    if not evidence_file.exists():
        return []

    records = []
    for line in evidence_file.read_text().strip().splitlines():
        if line:
            records.append(json.loads(line))

    return records

@router.get("/churn")
def get_churn(run_id: str) -> List[dict]:
    """Get churn records."""
    evidence_file = Path.home() / ".qaagent" / "runs" / run_id / "evidence" / "churn.jsonl"

    if not evidence_file.exists():
        return []

    records = []
    for line in evidence_file.read_text().strip().splitlines():
        if line:
            records.append(json.loads(line))

    return records

@router.get("/risks")
def get_risks(run_id: str, top_n: int = 10) -> List[dict]:
    """Get top N risks."""
    evidence_file = Path.home() / ".qaagent" / "runs" / run_id / "evidence" / "risks.jsonl"

    if not evidence_file.exists():
        return []

    risks = []
    for line in evidence_file.read_text().strip().splitlines():
        if line:
            risks.append(json.loads(line))

    # Already sorted by score descending (from RiskAggregator)
    return risks[:top_n]
```

**Acceptance Criteria**:
- [ ] GET /api/runs/{run_id}/findings returns quality.jsonl
- [ ] GET /api/runs/{run_id}/coverage returns coverage.jsonl
- [ ] GET /api/runs/{run_id}/churn returns churn.jsonl
- [ ] GET /api/runs/{run_id}/risks returns top N risks (default 10)
- [ ] Returns empty array if evidence file missing
- [ ] Unit tests with fixture runs

**Estimated Complexity**: Medium (2 hours)

---

#### S2-11: CLI Integration for Analyzers
**Goal**: Add CLI commands to run analyzers

**Files to modify**:
- `src/qaagent/cli.py`
- `src/qaagent/commands/analyze.py`

**Implementation**:
```python
# In commands/analyze.py

def run_risk_analysis(run_id: str) -> None:
    """Run risk aggregation on an existing run."""
    runs_dir = Path.home() / ".qaagent" / "runs"
    run_path = runs_dir / run_id

    if not run_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")

    # Load config
    risk_config = RiskConfig.load(Path("handoff/risk_config.yaml"))

    # Create handle (read-only)
    manager = RunManager(base_dir=runs_dir)
    handle = manager.load_run(run_id)  # New method needed

    # Run analyzers
    reader = EvidenceReader(handle)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    # Risk aggregation
    risk_aggregator = RiskAggregator(risk_config)
    risks = risk_aggregator.analyze(handle, reader, writer, id_gen)

    print(f"Generated {len(risks)} risk records")
    print(f"Top risk: {risks[0].component} (score: {risks[0].score})")
```

**CLI Command**:
```python
@analyze_app.command("risks")
def analyze_risks_command(
    run_id: Optional[str] = typer.Option(None, help="Run ID (defaults to latest)"),
):
    """Compute risk scores from evidence."""
    if not run_id:
        # Find latest run
        runs_dir = Path.home() / ".qaagent" / "runs"
        runs = sorted(runs_dir.iterdir(), reverse=True)
        if not runs:
            typer.echo("No runs found. Run 'qaagent analyze collectors' first.")
            raise typer.Exit(code=2)
        run_id = runs[0].name

    try:
        run_risk_analysis(run_id)
        typer.echo(f"Risk analysis complete for run: {run_id}")
    except Exception as exc:
        typer.echo(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2)
```

**Usage**:
```bash
# Run risk analysis on latest run
qaagent analyze risks

# Run on specific run
qaagent analyze risks --run-id 20251024_193012Z
```

**Acceptance Criteria**:
- [ ] `qaagent analyze risks` runs on latest run
- [ ] `qaagent analyze risks --run-id <id>` runs on specific run
- [ ] Outputs summary to console
- [ ] Writes risks.jsonl
- [ ] Returns non-zero exit code on error

**Estimated Complexity**: Medium (2 hours)

---

### Phase 6: Testing & Documentation

#### S2-12: Integration Tests
**Goal**: End-to-end tests for analyzers and API

**Files to create**:
- `tests/integration/analyzers/test_risk_aggregator.py`
- `tests/integration/analyzers/test_coverage_mapper.py`
- `tests/integration/api/test_endpoints.py`

**Test Scenarios**:

**Risk Aggregator**:
```python
def test_risk_aggregator_with_synthetic_repo(tmp_path):
    # 1. Run collectors (Sprint 1)
    run_id = run_collectors(synthetic_repo_path, tmp_path / "runs")

    # 2. Run risk analysis
    risk_config = RiskConfig.load(fixtures / "risk_config.yaml")
    handle = RunManager(tmp_path / "runs").load_run(run_id)
    reader = EvidenceReader(handle)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    aggregator = RiskAggregator(risk_config)
    risks = aggregator.analyze(handle, reader, writer, id_gen)

    # 3. Validate
    assert len(risks) > 0
    assert all(0 <= r.score <= 100 for r in risks)
    assert all(0 <= r.confidence <= 1.0 for r in risks)
    assert risks[0].score >= risks[-1].score  # Sorted descending

    # 4. Check risks.jsonl written
    risks_file = handle.evidence_dir / "risks.jsonl"
    assert risks_file.exists()
```

**API Endpoints**:
```python
def test_api_returns_runs(test_client):
    # Setup: Create a test run
    run_id = create_test_run(...)

    # Test
    response = test_client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    assert any(r["run_id"] == run_id for r in runs)

def test_api_returns_risks(test_client):
    run_id = create_test_run_with_risks(...)

    response = test_client.get(f"/api/runs/{run_id}/risks")
    assert response.status_code == 200
    risks = response.json()
    assert len(risks) <= 10  # Default top_n
    assert all("score" in r for r in risks)
```

**Acceptance Criteria**:
- [ ] Integration test runs full pipeline (collectors → risks)
- [ ] API tests cover all endpoints
- [ ] Tests use synthetic repo from Sprint 1
- [ ] All tests passing

**Estimated Complexity**: Medium (4 hours)

---

#### S2-13: Documentation
**Goal**: Update documentation for Sprint 2

**Files to update**:
- `docs/DEVELOPER_NOTES.md` - Add Sprint 2 section
- `handoff/RUNBOOK.md` - Add usage examples

**Content**:
```markdown
## Sprint 2: Risk Aggregation & API

### Risk Scoring Algorithm
1. Group findings by component (file path)
2. Apply weights from risk_config.yaml:
   - security: 3.0
   - coverage: 2.0
   - churn: 2.0
   - ...
3. Normalize to 0-100
4. Assign band (P0/P1/P2/P3)
5. Compute confidence (evidence diversity)

### API Endpoints
- GET /api/runs - List all runs
- GET /api/runs/{run_id} - Get run manifest
- GET /api/runs/{run_id}/findings - Get findings
- GET /api/runs/{run_id}/risks - Get top risks

### Usage
```bash
# 1. Collect evidence
qaagent analyze collectors /path/to/project

# 2. Compute risks
qaagent analyze risks

# 3. Start API server
qaagent api

# 4. Query via curl
curl http://localhost:8000/api/runs
curl http://localhost:8000/api/runs/20251024_193012Z/risks
```

**Acceptance Criteria**:
- [ ] DEVELOPER_NOTES.md updated with Sprint 2 architecture
- [ ] RUNBOOK.md updated with usage examples
- [ ] API documentation (OpenAPI/Swagger) auto-generated

**Estimated Complexity**: Low (2 hours)

---

## Checkpoint Strategy

### Checkpoint #1: Evidence Readers + Risk Models
**After**: S2-01, S2-02, S2-03
**Review**:
- Evidence reader can load all evidence types
- Risk models defined and validated
- Risk config loader working

### Checkpoint #2: Risk Aggregation Core
**After**: S2-04
**Review**:
- Risk aggregation algorithm working
- Scores computed correctly
- risks.jsonl written
- Integration test passes

### Checkpoint #3: Coverage & Recommendations
**After**: S2-05, S2-06, S2-07
**Review**:
- CUJ coverage mapping working
- Gaps identified correctly
- Recommendations generated

### Checkpoint #4: API Layer Complete
**After**: S2-08, S2-09, S2-10, S2-11
**Review**:
- API server running
- All endpoints working
- CLI integration working

### Checkpoint #5: Sprint 2 Complete
**After**: S2-12, S2-13
**Review**:
- All tests passing
- Documentation complete
- Ready for Sprint 3

---

## Dependencies & Risks

### Dependencies
- **Sprint 1 Complete**: ✅ All collectors working
- **Python Libraries**: FastAPI, uvicorn, pyyaml (already in project)
- **Config Files**: risk_config.yaml, cuj.yaml (already exist)

### Risks
| Risk | Mitigation |
|------|------------|
| Risk scoring algorithm too complex | Start simple (file-level), iterate |
| CUJ pattern matching edge cases | Use fnmatch, add tests for edge cases |
| API performance with large runs | Profile, add pagination if needed |
| Missing evidence files | Graceful degradation (return empty arrays) |

---

## Success Criteria

Sprint 2 is complete when:
- [ ] User can run `qaagent analyze risks` to compute risk scores
- [ ] risks.jsonl is generated with valid risk records
- [ ] API server serves all evidence via REST endpoints
- [ ] Coverage mapped to CUJs with gap identification
- [ ] Recommendations generated based on risks and gaps
- [ ] All integration tests passing
- [ ] Documentation updated

---

## Estimated Timeline

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | S2-01 | 1-2 hours |
| Phase 2 | S2-02, S2-03, S2-04 | 6-8 hours |
| Phase 3 | S2-05, S2-06 | 4-6 hours |
| Phase 4 | S2-07 | 2-3 hours |
| Phase 5 | S2-08, S2-09, S2-10, S2-11 | 5-6 hours |
| Phase 6 | S2-12, S2-13 | 6 hours |
| **Total** | | **24-31 hours** |

**Estimate**: 3-4 working days for Codex

---

## Next Steps

1. **Codex**: Review this plan
2. **Codex**: Ask clarifying questions if needed
3. **User**: Approve plan
4. **Codex**: Begin implementation starting with Phase 1
5. **Claude**: Review at checkpoints

---

## Notes for Codex

**Start Simple**:
- Risk aggregation: File-level risks first (not CUJ-level yet)
- API: Read-only, no mutations
- Recommendations: Rule-based (not LLM-generated yet)

**Follow Sprint 1 Patterns**:
- Use same error handling approach
- Write comprehensive tests
- Document as you go
- Same code quality standards

**When to Pause**:
- After each checkpoint (wait for Claude review)
- If you hit unexpected complexity
- If you need architecture decisions

**Questions to Resolve Before Starting**:
1. Should RunManager have a `load_run(run_id)` method? (Yes, add it)
2. Where should risk_config.yaml and cuj.yaml be loaded from? (From handoff/ for now, later from ~/.qaagent/config/)
3. Should API have pagination? (Not for MVP, add TODO)

Good luck! 🚀
