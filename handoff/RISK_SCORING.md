# Risk Scoring & Confidence Model

**Version:** 1.0.0-mvp
**Last Updated:** 2025-10-24
**Applies To:** Sprint 2+ (Risk Aggregation)

---

## Overview

This document formalizes how qaagent computes risk scores and confidence metrics from evidence collected in Sprint 1. The model is designed to be:

- **Transparent**: Every score can be traced to specific evidence
- **Configurable**: Weights and thresholds defined in `risk_config.yaml`
- **Explainable**: Metadata shows which inputs contributed to each score
- **Deterministic**: Same evidence always produces same score

---

## Risk Score Calculation

### Formula

```
normalized_score = weighted_sum(dimension_scores) / total_weight
final_score = min(normalized_score, max_total) * 100
```

Where:
- `dimension_scores`: Normalized scores (0.0-1.0) for each risk dimension
- `total_weight`: Sum of all enabled dimension weights
- `max_total`: Cap from config (default: 100)

### Dimensions

From `risk_config.yaml.scoring.weights`:

| Dimension | Weight | Data Source | Normalization |
|-----------|--------|-------------|---------------|
| Security | 3.0 | bandit findings, dependency CVEs | Severity-weighted count |
| Coverage | 2.0 | Coverage metrics vs targets | 1.0 - (actual_coverage / target_coverage) |
| Churn | 2.0 | Git commit/change frequency | Percentile rank in repository |
| Complexity | 1.5 | Cyclomatic complexity (future) | Thresholds: <10=0.0, 10-20=0.5, >20=1.0 |
| API Exposure | 1.0 | Public endpoints without auth | Count / total_endpoints |
| Accessibility | 0.5 | A11y violations (if available) | Severity-weighted count |
| Performance | 1.0 | Response time metrics (future) | Percentile vs baseline |

### Dimension Score Normalization

Each dimension must output a value between 0.0 (no risk) and 1.0 (maximum risk).

#### Security Normalization
```python
def normalize_security(findings: list[SecurityFinding]) -> float:
    """
    Weight findings by severity, normalize by repository size.
    """
    severity_weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}

    weighted_sum = sum(
        severity_weights.get(f.severity, 0.5)
        for f in findings
    )

    # Normalize by lines of code (LoC)
    loc = get_repository_loc()
    normalized = weighted_sum / (loc / 1000)  # per 1K LoC

    # Cap at 1.0
    return min(normalized, 1.0)
```

#### Coverage Normalization
```python
def normalize_coverage(metrics: CoverageMetrics, targets: dict) -> float:
    """
    Compute coverage gap as risk.
    Higher gap = higher risk.
    """
    gaps = []
    for cuj_id, target in targets.items():
        actual = metrics.get_cuj_coverage(cuj_id)
        if actual is None:
            gaps.append(1.0)  # Missing coverage = maximum risk
        else:
            gap = max(0, target - actual) / target
            gaps.append(gap)

    return sum(gaps) / len(gaps) if gaps else 0.0
```

#### Churn Normalization
```python
def normalize_churn(path: str, churn_data: ChurnMetrics, repository_stats: RepoStats) -> float:
    """
    Convert churn count to percentile rank.
    Files in top 10% churn = high risk.
    """
    all_churn_counts = [c.commits for c in repository_stats.all_files]
    percentile = percentile_rank(churn_data.commits, all_churn_counts)

    # Top 10% = 1.0, bottom 50% = 0.0, linear in between
    if percentile >= 90:
        return 1.0
    elif percentile <= 50:
        return 0.0
    else:
        return (percentile - 50) / 40  # Scale 50-90 to 0.0-1.0
```

### Weighted Aggregation Example

Given:
- Security findings: 3 high, 2 medium → normalized = 0.42
- Coverage gap: 62% actual vs 80% target → normalized = 0.225
- Churn: 85th percentile → normalized = 0.875
- Other dimensions: not available (score = 0.0)

```python
weights = {"security": 3.0, "coverage": 2.0, "churn": 2.0}
scores = {"security": 0.42, "coverage": 0.225, "churn": 0.875}

weighted_sum = (0.42 * 3.0) + (0.225 * 2.0) + (0.875 * 2.0)
             = 1.26 + 0.45 + 1.75
             = 3.46

total_weight = 3.0 + 2.0 + 2.0 = 7.0

normalized = 3.46 / 7.0 = 0.494

final_score = 0.494 * 100 = 49.4
```

**Result:** Score of 49.4 → Band **P2** (based on `risk_config.yaml` bands)

---

## Priority Bands

From `risk_config.yaml.prioritization.bands`:

```yaml
bands:
  - { name: "P0", min_score: 80 }   # Critical - immediate action
  - { name: "P1", min_score: 65 }   # High - address soon
  - { name: "P2", min_score: 50 }   # Medium - planned work
  - { name: "P3", min_score: 0 }    # Low - backlog
```

**Band Assignment:**
```python
def assign_band(score: float, bands: list[Band]) -> str:
    """
    Assign band based on score thresholds.
    Bands must be sorted descending by min_score.
    """
    for band in sorted(bands, key=lambda b: b.min_score, reverse=True):
        if score >= band.min_score:
            return band.name
    return bands[-1].name  # Default to lowest band
```

---

## Confidence Calculation

### Purpose

Confidence represents how much we trust the risk score. High confidence means:
- Multiple independent evidence sources
- Recent data
- High-quality tools with known accuracy

Low confidence means:
- Single source of evidence
- Stale data
- Tools with known false positive rates

### Formula

From `risk_config.yaml.confidence.factors`:

```yaml
confidence:
  factors:
    evidence_density_weight: 0.6
    recency_weight: 0.3
    tool_diversity_weight: 0.1
```

**Base Calculation:**
```python
confidence = (
    base_tool_confidence
    * (1 + evidence_density_bonus)
    * recency_factor
    * tool_diversity_factor
)

# Cap between 0.0 and 1.0
confidence = max(0.0, min(1.0, confidence))
```

### Components

#### 1. Base Tool Confidence

Default confidence values per tool type:

| Tool Category | Base Confidence | Rationale |
|---------------|-----------------|-----------|
| Dependency Scanner (pip-audit) | 0.90 | CVE database is authoritative |
| Security Linter (bandit) | 0.70 | Known false positives in security rules |
| Style Linter (flake8) | 0.80 | Well-established, low false positive rate |
| Type Checker (mypy, future) | 0.85 | Deterministic static analysis |
| Coverage Parser | 0.95 | Direct measurement, not heuristic |
| Git Churn | 0.75 | Correlation to risk, not causation |

**Multi-tool aggregation:**
```python
def base_confidence(related_evidence: list[Evidence]) -> float:
    """
    Average confidence of all tools contributing evidence.
    """
    if not related_evidence:
        return 0.5  # Default medium confidence

    tool_confidences = [
        TOOL_CONFIDENCE_MAP.get(e.tool, 0.5)
        for e in related_evidence
    ]

    return sum(tool_confidences) / len(tool_confidences)
```

#### 2. Evidence Density Bonus

More corroborating evidence = higher confidence.

```python
def evidence_density_bonus(evidence_count: int) -> float:
    """
    +0.1 per corroborating piece of evidence, max +0.3.
    """
    bonus_per_evidence = 0.1
    max_bonus = 0.3

    bonus = (evidence_count - 1) * bonus_per_evidence  # -1 because first evidence is baseline
    return min(bonus, max_bonus)
```

**Example:**
- 1 evidence item: bonus = 0.0
- 2 evidence items: bonus = 0.1
- 3 evidence items: bonus = 0.2
- 4+ evidence items: bonus = 0.3 (capped)

#### 3. Recency Factor

Older evidence is less confident (code may have changed).

```python
from datetime import datetime, timedelta

def recency_factor(evidence_timestamps: list[datetime]) -> float:
    """
    Weight by age of evidence.
    """
    now = datetime.utcnow()
    ages = [(now - ts).total_seconds() / 86400 for ts in evidence_timestamps]  # days
    avg_age = sum(ages) / len(ages)

    if avg_age < 7:
        return 1.0   # Fresh: <1 week
    elif avg_age < 30:
        return 0.9   # Recent: <1 month
    elif avg_age < 90:
        return 0.8   # Moderate: <3 months
    else:
        return 0.6   # Stale: >3 months
```

#### 4. Tool Diversity Factor

Evidence from multiple tool categories is more reliable than repeated findings from the same tool.

```python
def tool_diversity_factor(related_evidence: list[Evidence]) -> float:
    """
    Bonus for using multiple tool categories.
    """
    categories = {e.tool_category for e in related_evidence}
    diversity_count = len(categories)

    # 1 category = 1.0 (no bonus)
    # 2 categories = 1.05
    # 3+ categories = 1.10
    return 1.0 + min(0.10, (diversity_count - 1) * 0.05)
```

### Complete Example

```python
# Evidence for a risk:
evidence = [
    Evidence(tool="bandit", category="security", timestamp=7_days_ago, confidence=0.7),
    Evidence(tool="pip-audit", category="dependency", timestamp=2_days_ago, confidence=0.9),
    Evidence(tool="git", category="churn", timestamp=1_day_ago, confidence=0.75),
]

# Step 1: Base confidence
base = (0.7 + 0.9 + 0.75) / 3 = 0.783

# Step 2: Evidence density bonus
density_bonus = (3 - 1) * 0.1 = 0.2

# Step 3: Recency factor
avg_age = (7 + 2 + 1) / 3 = 3.33 days → factor = 1.0 (fresh)

# Step 4: Tool diversity factor
categories = {"security", "dependency", "churn"} → 3 categories
diversity_factor = 1.0 + (3 - 1) * 0.05 = 1.10

# Final confidence
confidence = 0.783 * (1 + 0.2) * 1.0 * 1.10
          = 0.783 * 1.2 * 1.0 * 1.10
          = 1.033 → capped at 1.0

# Result: 1.0 (maximum confidence)
```

---

## Risk Record Output

Each `RiskScore` in `risks.jsonl` includes:

```json
{
  "risk_id": "RSK-20251024-0003",
  "related_evidence": ["FND-20251024-0007", "CHN-20251024-0002"],
  "category": "security",
  "score": 78.2,
  "band": "P1",
  "confidence": 0.62,
  "summary": "High-churn auth module with failing bandit rule B101",
  "recommendation": "Add unit tests around auth handlers and fix hard-coded secrets.",
  "linked_cujs": ["auth_login"],
  "metadata": {
    "weights": {
      "security": 3.0,
      "churn": 2.0
    },
    "normalized_inputs": {
      "security": 0.85,
      "churn": 0.67
    },
    "confidence_breakdown": {
      "base": 0.725,
      "density_bonus": 0.1,
      "recency_factor": 1.0,
      "diversity_factor": 1.05
    }
  }
}
```

**Key Fields:**
- `metadata.weights`: Which dimensions contributed and their weights
- `metadata.normalized_inputs`: Normalized (0-1) scores per dimension before weighting
- `metadata.confidence_breakdown`: How confidence was calculated
- `related_evidence`: IDs of supporting evidence for traceability

---

## Edge Cases & Degradation

### Missing Dimension Data

If a dimension has no data (e.g., no coverage metrics available):
1. **Score**: Treated as 0.0 (neutral, not high risk)
2. **Weight**: Excluded from `total_weight` calculation
3. **Confidence**: Penalty applied via tool diversity factor

**Example:**
```python
# Only security data available, no coverage/churn
weights = {"security": 3.0, "coverage": 2.0, "churn": 2.0}
available = {"security": 0.8}

# Adjusted calculation
weighted_sum = 0.8 * 3.0 = 2.4
total_weight = 3.0  # Only count weights for available data

normalized = 2.4 / 3.0 = 0.8
final_score = 0.8 * 100 = 80.0

# But confidence is lowered due to single tool category
confidence = 0.7 * 1.0 * 1.0 * 1.0 = 0.7  # No diversity bonus
```

### Conflicting Evidence

If evidence conflicts (e.g., one tool says safe, another says vulnerable):
1. **Take maximum risk**: Assume vulnerable until proven safe
2. **Lower confidence**: Conflict indicates uncertainty
3. **Record in metadata**: Flag as `conflicting_evidence: true`

### No Evidence Available

If no evidence exists for a component:
1. **Do not create risk record**: Absence of evidence ≠ evidence of absence
2. **Optional**: Create `RSK-*` with `score: null`, `confidence: 0.0`, `summary: "Insufficient data"`

---

## Validation & Testing

### Unit Tests

Test individual normalization functions with known inputs:

```python
def test_security_normalization():
    findings = [
        SecurityFinding(severity="critical"),
        SecurityFinding(severity="high"),
    ]
    loc = 10000

    score = normalize_security(findings, loc)

    # critical=1.0, high=0.7 → sum=1.7
    # normalized = 1.7 / (10000/1000) = 1.7 / 10 = 0.17
    assert score == pytest.approx(0.17, 0.01)
```

### Integration Tests

Test full risk calculation pipeline:

```python
def test_risk_aggregation():
    evidence = create_test_evidence([
        ("bandit", "security", 0.7, 3_days_ago),
        ("coverage", "coverage", 0.95, 1_day_ago),
    ])

    risk = compute_risk(evidence, risk_config)

    assert risk.score > 0
    assert risk.band in ["P0", "P1", "P2", "P3"]
    assert 0.0 <= risk.confidence <= 1.0
    assert risk.metadata["confidence_breakdown"] is not None
```

### Regression Tests

Store baseline risks for synthetic repository:

```
tests/fixtures/synthetic_repo/expected_risks.json
```

Compare new runs against baseline to detect scoring drift.

---

## Configuration Override

Users can customize via `~/.qaagent/config/risk_config.yaml`:

```yaml
scoring:
  weights:
    security: 4.0      # Increase security weight
    coverage: 1.5      # Decrease coverage weight
    custom_metric: 2.0 # Add new dimension (requires custom analyzer)
```

**Validation:**
- Weights must be non-negative floats
- Unknown dimensions logged as warning but not rejected
- If weight=0.0, dimension is skipped

---

## Future Enhancements

### Machine Learning Scoring (Post-MVP)

Replace heuristic normalization with trained models:
- Historical bug correlation data
- Bayesian risk estimation
- Anomaly detection for unusual patterns

### Custom Risk Rules (Post-MVP)

Allow users to define domain-specific rules:

```yaml
custom_rules:
  - name: "Payment Processing High Risk"
    condition: "path.startswith('src/payments/') AND security_findings > 0"
    score_multiplier: 1.5
    band_override: "P0"
```

### Risk Trends (Post-MVP)

Compare current run vs previous runs:
- Risk score delta
- New vs resolved findings
- Coverage progression

---

**Status:** Ready for implementation in Sprint 2
**Dependencies:** Sprint 1 evidence store must be complete
**Next Steps:** Codex implements risk aggregator using this spec
