# Sprint 3 Plan: Dashboard, Reports & AI Summaries

**Created**: 2025-10-25
**Owner**: Codex (implementation) + Claude (checkpoints)
**Status**: Ready to start
**Depends on**: Sprint 2 (API Layer) ✅ COMPLETE (9.75/10)

---

## Overview

Sprint 3 completes the qaagent vision with a **beautiful, user-friendly product** for both technical and business stakeholders:

- **Dashboard**: Professional React UI with charts, graphs, and interactive visualizations
- **Reports**: Exportable PDF/HTML reports for executives and stakeholders
- **AI Summaries**: Local Ollama integration for intelligent risk analysis
- **Polish**: Production-ready deployment, security, monitoring, documentation

**Goal**: Create a **best-in-class QA platform** that delights both developers and business users.

---

## Sprint Goals

By the end of Sprint 3, users should be able to:

1. **Open a beautiful dashboard** showing top risks, coverage gaps, and trends
2. **Drill down into components** with interactive charts and detailed evidence
3. **Generate professional reports** (PDF) for management review
4. **Get AI-powered insights** citing evidence from the risk analysis
5. **Deploy to production** with Docker, monitoring, and security hardening
6. **Compare runs over time** to track quality improvements

---

## User Personas

### Primary: Business Stakeholders
- **Needs**: Visual dashboards, executive reports, trend analysis
- **Pain Points**: Technical jargon, command-line tools, raw data
- **Solution**: Beautiful UI with charts, one-click reports, plain-language summaries

### Secondary: Developers
- **Needs**: API access, CI/CD integration, detailed evidence
- **Pain Points**: Time-consuming manual QA, unclear priorities
- **Solution**: API endpoints, CLI tools, actionable recommendations

### Tertiary: QA Teams
- **Needs**: Test coverage insights, risk prioritization, workflow automation
- **Pain Points**: Manual testing, lack of visibility into critical paths
- **Solution**: CUJ coverage tracking, risk scores, automated recommendations

---

## Phase Breakdown

### Phase 1: Dashboard Foundation (Week 1)
**Goal**: Core dashboard with essential views

### Phase 2: Visualization & UX (Week 2)
**Goal**: Charts, graphs, and polished user experience

### Phase 3: Reports & Export (Week 3)
**Goal**: Professional report generation

### Phase 4: AI Summaries (Week 4)
**Goal**: Local Ollama integration with evidence citations

### Phase 5: Production Polish (Week 5)
**Goal**: Security, monitoring, deployment, documentation

---

## Detailed Task Breakdown

---

## Phase 1: Dashboard Foundation (Week 1)

### S3-01: Dashboard Architecture & Setup
**Goal**: Set up React app with routing and API integration

**Technology Stack**:
- **Frontend**: React 18 + TypeScript
- **Styling**: Tailwind CSS (modern, fast, customizable)
- **Charts**: Recharts or Chart.js
- **State**: React Query (for API caching)
- **Routing**: React Router
- **Build**: Vite (fast dev server)

**Directory Structure**:
```
src/qaagent/dashboard/
  ├── frontend/
  │   ├── src/
  │   │   ├── components/
  │   │   │   ├── Layout/        # Header, Sidebar, Footer
  │   │   │   ├── Runs/          # Runs list, run details
  │   │   │   ├── Risks/         # Risk list, risk details
  │   │   │   ├── Coverage/      # Coverage views
  │   │   │   └── Charts/        # Reusable chart components
  │   │   ├── pages/
  │   │   │   ├── Dashboard.tsx  # Main overview
  │   │   │   ├── Runs.tsx       # Runs list
  │   │   │   ├── RunDetails.tsx # Single run view
  │   │   │   └── Settings.tsx   # Configuration
  │   │   ├── services/
  │   │   │   └── api.ts         # API client
  │   │   ├── types/
  │   │   │   └── index.ts       # TypeScript types
  │   │   └── App.tsx
  │   ├── public/
  │   ├── package.json
  │   └── vite.config.ts
  └── server.py                   # Static file server
```

**Implementation**:
```typescript
// src/services/api.ts
class QAAgentAPI {
  private baseURL: string;

  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async getRuns(limit = 50, offset = 0) {
    const response = await fetch(
      `${this.baseURL}/api/runs?limit=${limit}&offset=${offset}`
    );
    return response.json();
  }

  async getRun(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}`);
    return response.json();
  }

  async getRisks(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/risks`);
    return response.json();
  }

  async getRecommendations(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/recommendations`);
    return response.json();
  }

  async getCoverage(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/coverage`);
    return response.json();
  }
}
```

**Acceptance Criteria**:
- [ ] React app scaffolded with Vite
- [ ] TypeScript configured
- [ ] Tailwind CSS integrated
- [ ] API client service working
- [ ] Basic routing (Dashboard, Runs, Settings)
- [ ] Can fetch and display runs list

**Estimated Complexity**: Medium (6-8 hours)

---

### S3-02: Dashboard Overview Page
**Goal**: Main dashboard showing key metrics at a glance

**Design**:
```
┌─────────────────────────────────────────────────────┐
│  QA Agent Dashboard                     [Settings]   │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 42 Runs  │  │ 18 P0/P1 │  │ 65% Avg  │          │
│  │ Total    │  │ Risks    │  │ Coverage │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                       │
│  Top Risks (Last Run)                    [View All] │
│  ┌─────────────────────────────────────────────────┐│
│  │ 🔴 P0  src/auth/login.py          Score: 85.0  ││
│  │ 🟠 P1  src/api/users.py           Score: 72.0  ││
│  │ 🟡 P2  src/services/payment.py    Score: 58.0  ││
│  └─────────────────────────────────────────────────┘│
│                                                       │
│  Coverage Gaps (CUJs)                    [View All] │
│  ┌─────────────────────────────────────────────────┐│
│  │ ⚠️  Login Flow           45% (target 80%)       ││
│  │ ⚠️  Payment Processing   52% (target 70%)       ││
│  └─────────────────────────────────────────────────┘│
│                                                       │
│  Recent Runs                             [View All] │
│  ┌─────────────────────────────────────────────────┐│
│  │ 2025-10-25 12:00 | sonicgrid | 42 findings     ││
│  │ 2025-10-24 18:30 | sonicgrid | 38 findings     ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**Components**:
- Metric cards (Total runs, P0/P1 count, Average coverage)
- Top risks table (sortable)
- Coverage gaps widget
- Recent runs list

**Implementation**:
```typescript
// src/pages/Dashboard.tsx
export default function Dashboard() {
  const { data: runs } = useQuery('runs', () => api.getRuns(10, 0));
  const latestRun = runs?.runs[0];
  const { data: risks } = useQuery(
    ['risks', latestRun?.run_id],
    () => api.getRisks(latestRun.run_id),
    { enabled: !!latestRun }
  );

  return (
    <div className="p-6 space-y-6">
      <MetricsRow runs={runs} risks={risks} />
      <TopRisksTable risks={risks?.risks.slice(0, 5)} />
      <CoverageGapsWidget runId={latestRun?.run_id} />
      <RecentRunsList runs={runs?.runs} />
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Dashboard shows key metrics
- [ ] Top 5 risks displayed with severity badges
- [ ] Coverage gaps highlighted
- [ ] Recent runs listed with metadata
- [ ] Responsive design (desktop + mobile)

**Estimated Complexity**: Medium (8-10 hours)

---

### S3-03: Runs List & Details Pages
**Goal**: Browse all runs and drill into specific run details

**Runs List Page**:
```
┌─────────────────────────────────────────────────────┐
│  Analysis Runs                          [New Run]   │
├─────────────────────────────────────────────────────┤
│  Search: [___________]  Filter: [All Projects ▾]    │
│                                                       │
│  Run ID            | Project    | Date       | Risks│
│  ─────────────────────────────────────────────────  │
│  20251025_120000Z  | sonicgrid  | 2h ago     | 18   │
│  20251024_183000Z  | sonicgrid  | 1d ago     | 15   │
│  20251023_090000Z  | sonicgrid  | 2d ago     | 22   │
│                                                       │
│  Showing 1-10 of 42              [← 1 2 3 4 5 →]    │
└─────────────────────────────────────────────────────┘
```

**Run Details Page**:
```
┌─────────────────────────────────────────────────────┐
│  Run: 20251025_120000Z                [Export PDF]  │
│  sonicgrid | 2025-10-25 12:00:00                    │
├─────────────────────────────────────────────────────┤
│  [Overview] [Risks] [Coverage] [Findings] [Churn]   │
│                                                       │
│  Summary                                             │
│  • 42 findings (12 high, 18 medium, 12 low)         │
│  • 65% average coverage                              │
│  • 18 components analyzed                            │
│  • 10 high-risk components identified                │
│                                                       │
│  Risk Score Distribution                             │
│  ┌─────────────────────────────────────────────────┐│
│  │      [Bar chart showing P0/P1/P2/P3 counts]     ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**Acceptance Criteria**:
- [ ] Runs list with search/filter
- [ ] Pagination working
- [ ] Click run → navigate to details
- [ ] Run details shows summary, tabs for evidence types
- [ ] Export button (placeholder for Phase 3)

**Estimated Complexity**: Medium (8-10 hours)

---

### S3-04: Risks View with Drill-Down
**Goal**: Interactive risks table with filtering and detail panels

**Design**:
```
┌─────────────────────────────────────────────────────┐
│  Risks for run 20251025_120000Z                     │
├─────────────────────────────────────────────────────┤
│  Filter: [All Severities ▾] [All Bands ▾]           │
│  Sort by: [Score ▾]                                  │
│                                                       │
│  Component              | Band | Score | Confidence  │
│  ─────────────────────────────────────────────────  │
│  src/auth/login.py      | P0   | 85.0  | ████ 1.0   │
│  src/api/users.py       | P1   | 72.0  | ███░ 0.7   │
│  src/services/payment.py| P2   | 58.0  | ███░ 0.8   │
│                                                       │
│  [Click row to expand details]                       │
│                                                       │
│  ┌─ src/auth/login.py (P0) ──────────────────────┐  │
│  │ Score: 85.0  |  Confidence: 1.0  |  Band: P0  │  │
│  │                                                │  │
│  │ Factors:                                       │  │
│  │ • Security: 60.0 (2 critical findings)        │  │
│  │ • Coverage: 15.0 (35% coverage, target 70%)   │  │
│  │ • Churn: 10.0 (15 commits in 90d)             │  │
│  │                                                │  │
│  │ Recommendations:                               │  │
│  │ • Add integration tests for authentication    │  │
│  │ • Increase unit test coverage to 70%          │  │
│  │                                                │  │
│  │ Evidence: [2 findings] [1 coverage] [1 churn] │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Acceptance Criteria**:
- [ ] Risks table with sorting/filtering
- [ ] Expandable rows showing details
- [ ] Factor breakdown with visual bars
- [ ] Link to related evidence
- [ ] Confidence visualization

**Estimated Complexity**: Medium-High (10-12 hours)

---

**Phase 1 Total**: ~40 hours (1 week)

---

## Phase 2: Visualization & UX (Week 2)

### S3-05: Charts & Graphs
**Goal**: Add visual analytics with charts

**Charts to Implement**:

1. **Risk Score Distribution** (Bar Chart)
   ```typescript
   <BarChart data={risksByBand}>
     <XAxis dataKey="band" />
     <YAxis />
     <Bar dataKey="count" fill="#ef4444" />
   </BarChart>
   ```

2. **Coverage Over Time** (Line Chart)
   ```typescript
   <LineChart data={coverageTrend}>
     <XAxis dataKey="date" />
     <YAxis />
     <Line dataKey="coverage" stroke="#10b981" />
   </LineChart>
   ```

3. **Risk Heatmap** (Grid)
   ```
   High Churn   [🔴][🟠][🟡]
   Med Churn    [🟠][🟡][🟢]
   Low Churn    [🟡][🟢][🟢]
                Low  Med  High
                 Coverage Gap
   ```

4. **Factor Composition** (Stacked Bar)
   ```typescript
   <BarChart data={riskFactors}>
     <Bar dataKey="security" stackId="a" fill="#dc2626" />
     <Bar dataKey="coverage" stackId="a" fill="#f59e0b" />
     <Bar dataKey="churn" stackId="a" fill="#3b82f6" />
   </BarChart>
   ```

5. **CUJ Coverage Gauge** (Radial)
   ```typescript
   <RadialBarChart data={cujCoverage}>
     <RadialBar dataKey="coverage" />
   </RadialBarChart>
   ```

**Acceptance Criteria**:
- [ ] All 5 chart types implemented
- [ ] Charts responsive and interactive
- [ ] Tooltips showing detailed data
- [ ] Color scheme consistent with risk severity
- [ ] Charts export to PNG (future)

**Estimated Complexity**: Medium (12-14 hours)

---

### S3-06: CUJ Coverage View
**Goal**: Visual representation of coverage mapped to CUJs

**Design**:
```
┌─────────────────────────────────────────────────────┐
│  Critical User Journeys                              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  Login Flow                         [View Details]   │
│  Coverage: 45% ██████░░░░░░░░  Target: 80%          │
│  Gap: 35%  ⚠️ Below target                           │
│  Components: 3 of 5 covered                          │
│                                                       │
│  Payment Processing                 [View Details]   │
│  Coverage: 52% ███████░░░░░░░  Target: 70%          │
│  Gap: 18%  ⚠️ Below target                           │
│  Components: 4 of 7 covered                          │
│                                                       │
│  Dashboard View                     [View Details]   │
│  Coverage: 78% █████████████░  Target: 60%          │
│  Gap: 0%   ✅ Above target                           │
│  Components: 8 of 10 covered                         │
└─────────────────────────────────────────────────────┘
```

**Detail View**:
```
┌─────────────────────────────────────────────────────┐
│  Login Flow Coverage Details                         │
├─────────────────────────────────────────────────────┤
│  Target: 80%  |  Actual: 45%  |  Gap: 35%           │
│                                                       │
│  Matched Components:                                 │
│  Component              | Coverage | Target | Gap    │
│  ───────────────────────────────────────────────────│
│  src/auth/login.py      | 35%      | 70%    | -35%  │
│  src/auth/session.py    | 60%      | 70%    | -10%  │
│  src/api/auth/routes.py | 40%      | 70%    | -30%  │
│                                                       │
│  APIs:                                               │
│  • POST /api/auth/login                              │
│                                                       │
│  Acceptance Criteria:                                │
│  ✅ Valid credentials produce 200 and token         │
│  ✅ Invalid credentials produce 401                 │
│  ⚠️  Rate limiting enforced                          │
│                                                       │
│  Recommendations:                                    │
│  • Add integration tests for rate limiting          │
│  • Increase unit test coverage for login.py         │
└─────────────────────────────────────────────────────┘
```

**Acceptance Criteria**:
- [ ] CUJ list with coverage bars
- [ ] Color-coded by gap (red/yellow/green)
- [ ] Expandable details showing components
- [ ] Acceptance criteria checklist
- [ ] Recommendations highlighted

**Estimated Complexity**: Medium (10-12 hours)

---

### S3-07: Trend Analysis (Multi-Run Comparison)
**Goal**: Compare metrics across multiple runs

**Design**:
```
┌─────────────────────────────────────────────────────┐
│  Trend Analysis                                      │
├─────────────────────────────────────────────────────┤
│  Select Runs: [Last 10 runs ▾]                      │
│                                                       │
│  Risk Score Trend                                    │
│  ┌─────────────────────────────────────────────────┐│
│  │      [Line chart: avg risk score over time]     ││
│  └─────────────────────────────────────────────────┘│
│                                                       │
│  Coverage Trend                                      │
│  ┌─────────────────────────────────────────────────┐│
│  │      [Line chart: avg coverage over time]       ││
│  └─────────────────────────────────────────────────┘│
│                                                       │
│  P0/P1 Risk Count Trend                              │
│  ┌─────────────────────────────────────────────────┐│
│  │      [Area chart: P0/P1 counts over time]       ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**Implementation**:
- New API endpoint: `GET /api/runs/trends?run_ids=...`
- Aggregate metrics across runs
- Time-series visualizations

**Acceptance Criteria**:
- [ ] Multi-run comparison
- [ ] Trend charts for key metrics
- [ ] Date range selector
- [ ] Export trend data (CSV)

**Estimated Complexity**: Medium-High (12-14 hours)

---

### S3-08: UX Polish & Responsive Design
**Goal**: Professional look and feel

**Tasks**:
1. **Color Scheme**
   - P0 (Critical): Red (#dc2626)
   - P1 (High): Orange (#f59e0b)
   - P2 (Medium): Yellow (#fbbf24)
   - P3 (Low): Green (#10b981)
   - Neutral: Slate (#64748b)

2. **Loading States**
   - Skeleton screens while loading
   - Progress indicators
   - Error boundaries

3. **Empty States**
   - No runs → "Run your first analysis"
   - No risks → "Great! No high-priority risks"
   - No data → Helpful messages

4. **Accessibility**
   - ARIA labels
   - Keyboard navigation
   - Screen reader support
   - Color contrast compliance

5. **Responsive Design**
   - Desktop (1920px+)
   - Laptop (1280px)
   - Tablet (768px)
   - Mobile (375px)

**Acceptance Criteria**:
- [ ] Consistent color scheme
- [ ] Loading states for all async operations
- [ ] Empty states with CTAs
- [ ] WCAG AA compliant
- [ ] Mobile-friendly

**Estimated Complexity**: Medium (10-12 hours)

---

**Phase 2 Total**: ~50 hours (1.25 weeks)

---

## Phase 3: Reports & Export (Week 3)

### S3-09: Report Generation Service
**Goal**: Backend service to generate PDF/HTML reports

**Technology**:
- **PDF**: WeasyPrint or Playwright (headless browser)
- **HTML**: Jinja2 templates
- **Storage**: Save to run directory

**Directory Structure**:
```
src/qaagent/reports/
  ├── __init__.py
  ├── generator.py          # Report generator
  ├── templates/
  │   ├── executive_summary.html
  │   ├── technical_report.html
  │   └── components/
  │       ├── header.html
  │       ├── risk_table.html
  │       └── charts.html
  └── styles/
      └── report.css
```

**Implementation**:
```python
# src/qaagent/reports/generator.py
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

class ReportGenerator:
    def __init__(self, template_dir: Path):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_executive_summary(
        self,
        run_data: Dict[str, Any],
        output_path: Path,
        format: str = "pdf"
    ) -> Path:
        """Generate executive summary report."""
        template = self.env.get_template("executive_summary.html")
        html_content = template.render(**run_data)

        if format == "pdf":
            HTML(string=html_content).write_pdf(output_path)
        else:
            output_path.write_text(html_content)

        return output_path

    def generate_technical_report(
        self,
        run_data: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """Generate detailed technical report."""
        template = self.env.get_template("technical_report.html")
        html_content = template.render(**run_data)
        HTML(string=html_content).write_pdf(output_path)
        return output_path
```

**Report Templates**:

**Executive Summary** (1-2 pages):
- High-level metrics
- Top 5 risks
- Coverage summary
- Recommendations
- Trend charts

**Technical Report** (5-10 pages):
- Detailed findings
- Risk breakdown by component
- Coverage analysis
- Churn analysis
- Full recommendations
- Evidence appendix

**Acceptance Criteria**:
- [ ] Generate PDF reports
- [ ] Generate HTML reports
- [ ] Professional styling
- [ ] Charts embedded in reports
- [ ] Company logo/branding support

**Estimated Complexity**: Medium-High (14-16 hours)

---

### S3-10: Report API Endpoints
**Goal**: API to request and download reports

**Implementation**:
```python
# src/qaagent/api/routes/reports.py
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse

router = APIRouter(tags=["reports"])

@router.post("/runs/{run_id}/reports/generate")
async def generate_report(
    run_id: str,
    report_type: str = "executive",  # executive | technical
    format: str = "pdf",              # pdf | html
    background_tasks: BackgroundTasks = None
):
    """Queue report generation (async)."""
    task_id = generate_report_task(run_id, report_type, format)
    return {"task_id": task_id, "status": "queued"}

@router.get("/runs/{run_id}/reports/{report_type}.{format}")
async def download_report(run_id: str, report_type: str, format: str):
    """Download generated report."""
    report_path = get_report_path(run_id, report_type, format)
    if not report_path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(report_path)

@router.get("/runs/{run_id}/reports")
async def list_reports(run_id: str):
    """List available reports for a run."""
    return {"reports": list_available_reports(run_id)}
```

**Dashboard Integration**:
```typescript
// Frontend: Export button
async function exportReport(runId: string, type: 'executive' | 'technical') {
  const response = await api.generateReport(runId, type, 'pdf');
  const taskId = response.task_id;

  // Poll for completion
  const interval = setInterval(async () => {
    const status = await api.getReportStatus(taskId);
    if (status === 'complete') {
      clearInterval(interval);
      window.open(`/api/runs/${runId}/reports/${type}.pdf`);
    }
  }, 1000);
}
```

**Acceptance Criteria**:
- [ ] POST endpoint to generate reports
- [ ] GET endpoint to download reports
- [ ] Background task processing
- [ ] Progress tracking
- [ ] Dashboard export buttons working

**Estimated Complexity**: Medium (8-10 hours)

---

### S3-11: Export to CSV/JSON
**Goal**: Export data in machine-readable formats

**Implementation**:
```python
# src/qaagent/api/routes/exports.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import csv
import io

router = APIRouter(tags=["exports"])

@router.get("/runs/{run_id}/risks.csv")
async def export_risks_csv(run_id: str):
    """Export risks as CSV."""
    risks = get_risks(run_id)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'risk_id', 'component', 'score', 'band', 'confidence', 'severity'
    ])
    writer.writeheader()
    for risk in risks:
        writer.writerow(risk)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=risks_{run_id}.csv"}
    )

@router.get("/runs/{run_id}/export.json")
async def export_full_run(run_id: str):
    """Export complete run data as JSON."""
    data = {
        "manifest": get_manifest(run_id),
        "findings": get_findings(run_id),
        "coverage": get_coverage(run_id),
        "churn": get_churn(run_id),
        "risks": get_risks(run_id),
        "recommendations": get_recommendations(run_id)
    }
    return data
```

**Acceptance Criteria**:
- [ ] CSV export for risks, findings, coverage
- [ ] JSON export for complete run
- [ ] Excel export (optional)
- [ ] Dashboard download buttons

**Estimated Complexity**: Low-Medium (6-8 hours)

---

**Phase 3 Total**: ~30 hours (0.75 weeks)

---

## Phase 4: AI Summaries (Week 4)

### S3-12: Ollama Integration
**Goal**: Local LLM for intelligent risk summaries

**Setup**:
```python
# src/qaagent/llm/ollama_client.py
import requests
from typing import Dict, List

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:7b"

    def generate(self, prompt: str, system: str = None) -> str:
        """Generate completion from Ollama."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        return response.json()["response"]

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            requests.get(f"{self.base_url}/api/tags", timeout=2)
            return True
        except:
            return False
```

**Acceptance Criteria**:
- [ ] Ollama client implemented
- [ ] Health check for Ollama availability
- [ ] Fallback if Ollama not running
- [ ] Model configurable

**Estimated Complexity**: Low (4-6 hours)

---

### S3-13: Risk Summary Prompts
**Goal**: Generate plain-language summaries of risks

**Prompt Templates**:
```python
# src/qaagent/llm/prompts.py
RISK_SUMMARY_PROMPT = """
You are a QA engineer analyzing code quality risks.

Component: {component}
Risk Score: {score}/100
Band: {band} (P0=Critical, P1=High, P2=Medium, P3=Low)

Evidence:
- Security Findings: {security_findings}
- Coverage: {coverage}% (target: 70%)
- Churn: {commits} commits, {lines_added} lines added in 90d

Task: Write a 2-3 sentence summary explaining:
1. Why this component is risky
2. The main concern (security, coverage, or churn)
3. What should be done about it

Cite evidence IDs when referring to specific issues.

Summary:
"""

CUJ_SUMMARY_PROMPT = """
You are a QA engineer analyzing test coverage for critical user journeys.

Journey: {cuj_name}
Current Coverage: {coverage}%
Target Coverage: {target}%
Gap: {gap}%

Components:
{components}

Task: Write a 2-3 sentence summary explaining:
1. Why this coverage gap is concerning
2. Which components need more testing
3. Business impact if this journey fails

Summary:
"""
```

**Implementation**:
```python
# src/qaagent/analyzers/summarizer.py
from qaagent.llm.ollama_client import OllamaClient
from qaagent.llm.prompts import RISK_SUMMARY_PROMPT

class RiskSummarizer:
    def __init__(self, client: OllamaClient):
        self.client = client

    def summarize_risk(self, risk: RiskRecord, findings: List[FindingRecord]) -> str:
        """Generate AI summary for a risk."""
        if not self.client.is_available():
            return self._fallback_summary(risk)

        prompt = RISK_SUMMARY_PROMPT.format(
            component=risk.component,
            score=risk.score,
            band=risk.band,
            security_findings=len([f for f in findings if f.file == risk.component]),
            coverage=risk.factors.get("coverage", 0),
            commits=0,  # TODO: get from churn data
            lines_added=0
        )

        return self.client.generate(prompt)

    def _fallback_summary(self, risk: RiskRecord) -> str:
        """Fallback summary if Ollama unavailable."""
        return f"{risk.component} has a risk score of {risk.score} ({risk.band}). " \
               f"Main factors: {', '.join(risk.factors.keys())}."
```

**Acceptance Criteria**:
- [ ] Risk summary generation working
- [ ] CUJ summary generation working
- [ ] Evidence citations in summaries
- [ ] Fallback if Ollama unavailable
- [ ] Summaries cached (not re-generated)

**Estimated Complexity**: Medium (10-12 hours)

---

### S3-14: AI-Powered Recommendations
**Goal**: Enhance recommendations with AI suggestions

**Implementation**:
```python
RECOMMENDATION_PROMPT = """
You are a QA engineer suggesting testing strategies.

Component: {component}
Risk Score: {score}
Factors:
- Security issues: {security_count}
- Coverage: {coverage}%
- Churn: {churn_normalized}

Evidence:
{evidence_summary}

Task: Suggest 3 specific, actionable testing recommendations.
Be concrete (e.g., "Add integration tests for login flow", not "improve tests").

Recommendations:
1.
2.
3.
"""
```

**Acceptance Criteria**:
- [ ] AI-enhanced recommendations
- [ ] Specific, actionable suggestions
- [ ] Fallback to rule-based recommendations
- [ ] Displayed in dashboard

**Estimated Complexity**: Medium (8-10 hours)

---

### S3-15: Privacy & Configuration
**Goal**: Ensure local-only AI with proper privacy controls

**Configuration**:
```yaml
# risk_config.yaml
ai:
  enabled: true
  provider: ollama  # ollama | disabled
  model: qwen2.5:7b
  ollama_url: http://localhost:11434
  max_tokens: 500
  temperature: 0.7

privacy:
  allow_external_ai: false
  redact_secrets: true
  log_prompts: false
```

**Implementation**:
```python
# src/qaagent/config/ai_config.py
from dataclasses import dataclass

@dataclass
class AIConfig:
    enabled: bool = True
    provider: str = "ollama"
    model: str = "qwen2.5:7b"
    ollama_url: str = "http://localhost:11434"

    @classmethod
    def load(cls, config_path: Path) -> "AIConfig":
        # Load from risk_config.yaml
        pass

    def validate_privacy(self):
        """Ensure privacy policies are enforced."""
        if self.provider not in ["ollama", "disabled"]:
            raise ValueError("Only local Ollama or disabled AI allowed")
```

**Acceptance Criteria**:
- [ ] AI configurable via YAML
- [ ] Privacy validation enforced
- [ ] No external API calls
- [ ] Secrets redaction in logs
- [ ] User consent for AI features

**Estimated Complexity**: Low-Medium (6-8 hours)

---

**Phase 4 Total**: ~30 hours (0.75 weeks)

---

## Phase 5: Production Polish (Week 5)

### S3-16: Security Hardening
**Goal**: Production-ready security

**Tasks**:

1. **API Authentication**
```python
# src/qaagent/api/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("QAAGENT_API_KEY"):
        raise HTTPException(403, "Invalid API key")
    return api_key

# Apply to routes
@router.get("/runs", dependencies=[Depends(verify_api_key)])
def list_runs():
    ...
```

2. **Rate Limiting**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/runs")
@limiter.limit("100/minute")
def list_runs():
    ...
```

3. **CORS Configuration**
```python
# Environment-based CORS
origins = os.getenv("QAAGENT_CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

4. **Input Validation**
```python
from pydantic import validator

class RunIDValidator(BaseModel):
    run_id: str

    @validator("run_id")
    def validate_run_id(cls, v):
        if not re.match(r"^\d{8}_\d{6}Z$", v):
            raise ValueError("Invalid run ID format")
        return v
```

**Acceptance Criteria**:
- [ ] API key authentication
- [ ] Rate limiting (100 req/min)
- [ ] CORS configurable
- [ ] Input validation on all endpoints
- [ ] HTTPS support (reverse proxy)

**Estimated Complexity**: Medium (10-12 hours)

---

### S3-17: Monitoring & Logging
**Goal**: Production observability

**Structured Logging**:
```python
# src/qaagent/utils/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        return json.dumps(log_obj)

# Configure
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("/var/log/qaagent/api.log"),
        logging.StreamHandler()
    ]
)
```

**Metrics Endpoint**:
```python
@app.get("/metrics")
def metrics():
    return {
        "uptime_seconds": time.time() - app.state.start_time,
        "total_requests": app.state.request_count,
        "total_runs": count_runs(),
        "cache_hit_rate": get_cache_stats(),
        "version": "1.0.0"
    }
```

**Health Check Enhancement**:
```python
@app.get("/health")
def health():
    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "checks": {
            "api": "ok",
            "runs_dir": check_runs_dir(),
            "disk_space": check_disk_space(),
            "ollama": "ok" if ollama_client.is_available() else "unavailable"
        }
    }
    return health_status
```

**Acceptance Criteria**:
- [ ] JSON structured logging
- [ ] Log rotation configured
- [ ] Metrics endpoint
- [ ] Enhanced health check
- [ ] Request tracing (request_id)

**Estimated Complexity**: Medium (8-10 hours)

---

### S3-18: Deployment & Docker
**Goal**: Production deployment packaging

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt

# Copy application
COPY . .
RUN pip install -e .

# Create runs directory
RUN mkdir -p /var/lib/qaagent/runs

# Expose API port
EXPOSE 8000

# Run API server
CMD ["qaagent", "api", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yaml**:
```yaml
version: '3.8'

services:
  qaagent-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./runs:/var/lib/qaagent/runs
      - ./config:/app/handoff
    environment:
      - QAAGENT_RUNS_DIR=/var/lib/qaagent/runs
      - QAAGENT_API_KEY=${API_KEY}
      - QAAGENT_CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
      - QAAGENT_LOG_LEVEL=${LOG_LEVEL:-INFO}
    restart: unless-stopped

  qaagent-dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - qaagent-api
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama-data:
```

**Nginx Reverse Proxy**:
```nginx
server {
    listen 80;
    server_name qaagent.example.com;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
}
```

**Acceptance Criteria**:
- [ ] Dockerfile for API
- [ ] Dockerfile for Dashboard
- [ ] docker-compose.yaml
- [ ] Nginx config example
- [ ] Environment variables documented
- [ ] Deployment guide (DEPLOYMENT.md)

**Estimated Complexity**: Medium (10-12 hours)

---

### S3-19: Documentation
**Goal**: Complete production documentation

**Documents to Create/Update**:

1. **DEPLOYMENT.md**
   - Docker deployment
   - Systemd service
   - Nginx setup
   - Environment variables
   - Troubleshooting

2. **API_DOCUMENTATION.md**
   - All endpoints
   - Request/response examples
   - Authentication
   - Rate limits
   - Error codes

3. **DASHBOARD_GUIDE.md**
   - User guide
   - Screenshots
   - Feature walkthrough
   - Export options

4. **DEVELOPER_NOTES.md**
   - Architecture overview
   - Code structure
   - Testing guide
   - Contributing guide

5. **README.md** (Update)
   - Sprint 3 features
   - Screenshots
   - Quick start
   - Full workflow example

**Acceptance Criteria**:
- [ ] All 5 documents complete
- [ ] Screenshots in guides
- [ ] Code examples tested
- [ ] Deployment tested on fresh VM

**Estimated Complexity**: Medium (12-14 hours)

---

### S3-20: End-to-End Testing
**Goal**: Comprehensive integration tests

**Test Scenarios**:

1. **Full Workflow Test**
```python
def test_complete_workflow(tmp_path):
    # 1. Run collectors
    result = run_cli(["analyze", "collectors", "--repo", str(tmp_path)])
    assert result.returncode == 0

    # 2. Extract run_id
    run_id = extract_run_id(result.stdout)

    # 3. Start API server (background)
    api_process = start_api_server()

    # 4. Test API endpoints
    response = requests.get(f"http://localhost:8000/api/runs/{run_id}")
    assert response.status_code == 200

    # 5. Generate report
    response = requests.post(f"http://localhost:8000/api/runs/{run_id}/reports/generate")
    assert response.status_code == 200

    # 6. Test dashboard (Playwright)
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:3000")
    assert page.locator("h1").text_content() == "QA Agent Dashboard"

    # Cleanup
    api_process.kill()
```

2. **Load Test**
```python
from locust import HttpUser, task

class QAAgentUser(HttpUser):
    @task
    def get_runs(self):
        self.client.get("/api/runs")

    @task
    def get_risks(self):
        self.client.get("/api/runs/20251025_120000Z/risks")
```

**Acceptance Criteria**:
- [ ] End-to-end workflow test
- [ ] Load test (100 concurrent users)
- [ ] Dashboard UI tests (Playwright)
- [ ] Report generation test
- [ ] All tests passing

**Estimated Complexity**: Medium-High (12-14 hours)

---

**Phase 5 Total**: ~50 hours (1.25 weeks)

---

## Sprint 3 Summary

### Total Effort Estimate

| Phase | Tasks | Hours | Weeks |
|-------|-------|-------|-------|
| Phase 1: Dashboard Foundation | S3-01 to S3-04 | 40 | 1.0 |
| Phase 2: Visualization & UX | S3-05 to S3-08 | 50 | 1.25 |
| Phase 3: Reports & Export | S3-09 to S3-11 | 30 | 0.75 |
| Phase 4: AI Summaries | S3-12 to S3-15 | 30 | 0.75 |
| Phase 5: Production Polish | S3-16 to S3-20 | 50 | 1.25 |
| **Total** | **20 tasks** | **200 hours** | **5 weeks** |

**Timeline**: ~5 weeks at full capacity (40 hrs/week)

---

## Checkpoints

**Checkpoint 1** (After Phase 1 - Week 1):
- Dashboard foundation complete
- Basic views working
- API integration tested

**Checkpoint 2** (After Phase 2 - Week 2.25):
- Charts and visualizations complete
- UX polished
- Responsive design working

**Checkpoint 3** (After Phase 3 - Week 3):
- Report generation working
- PDF/HTML exports tested
- Export features complete

**Checkpoint 4** (After Phase 4 - Week 3.75):
- AI summaries working
- Privacy controls enforced
- Ollama integration tested

**Checkpoint 5 (Final)** (After Phase 5 - Week 5):
- Production deployment tested
- Documentation complete
- Ready for launch

---

## Technology Stack

**Frontend**:
- React 18 + TypeScript
- Tailwind CSS
- Recharts / Chart.js
- React Query
- React Router
- Vite

**Backend** (already complete from Sprint 2):
- FastAPI
- Python 3.11+

**Reports**:
- WeasyPrint (PDF)
- Jinja2 (templates)

**AI**:
- Ollama (local LLM)
- qwen2.5:7b model

**Deployment**:
- Docker + docker-compose
- Nginx
- Systemd (optional)

---

## Success Criteria

Sprint 3 is complete when:

1. ✅ **Dashboard is beautiful and functional**
   - Professional design
   - Responsive
   - All key views working

2. ✅ **Reports are professional quality**
   - PDF generation
   - Executive and technical formats
   - Charts embedded

3. ✅ **AI summaries are helpful**
   - Local-only (Ollama)
   - Evidence citations
   - Privacy-compliant

4. ✅ **Production deployment is smooth**
   - Docker deployment working
   - Documentation complete
   - Security hardened

5. ✅ **Users love it**
   - Developers can use API
   - Stakeholders can view dashboards
   - Reports are actionable

---

## Next Steps

1. **Review this plan** with user
2. **Adjust priorities** if needed
3. **Start Phase 1** (Dashboard Foundation)
4. **Checkpoint after each phase**
5. **Launch to production** after Sprint 3

---

**Status**: Ready for approval
**Estimated Timeline**: 5 weeks
**Quality Target**: 9.5+/10 (match Sprint 1 & 2 excellence)
