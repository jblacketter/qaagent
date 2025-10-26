# Handoff to Codex: Sprint 3 - Dashboard, Reports & AI

**Date**: 2025-10-25
**From**: Claude (Planner) + User (Product Owner)
**To**: Codex (Implementation)
**Status**: ✅ APPROVED - Ready to start

---

## Context

**Sprint 1**: Evidence Collection ✅ Complete (9.5/10)
**Sprint 2**: Risk Analysis & API ✅ Complete (9.75/10)
**Sprint 3**: Dashboard, Reports & AI ← **YOU ARE HERE**

**User's Vision**:
> "We want well-developed UI, nice looking reports for less technical users. Good visuals and reports are key here. I don't mind spending extra time to fully refine this before production."

**Translation**: Build a **best-in-class QA platform** with professional UI and reports.

---

## User Decisions

### ✅ Approved Decisions

**Design**:
- Color scheme: Modern blue/red (your choice on specifics)
- Light/dark mode: **BOTH** (important!)
- Company branding: None (make logo optional/configurable)
- Professional, polished look

**Deployment**:
- **Local first**: Run on Mac/Windows with `npm run dev` + `qaagent api`
- No Docker required for development
- Cloud deployment comes later (Phase 5)
- Keep it simple for local development

**Features**:
- Follow SPRINT3_PLAN.md (all 20 tasks)
- Focus on quality over speed
- 5 weeks is acceptable timeline

**Team Access**:
- Single user (the developer)
- No authentication required for local development
- No user accounts needed
- Can run open on localhost

---

## Sprint 3 Overview

**Goal**: Build complete, production-ready QA platform with dashboard, reports, and AI

**Timeline**: 5 weeks (200 hours)

**Phases**:
1. Dashboard Foundation (Week 1)
2. Visualization & UX (Week 2)
3. Reports & Export (Week 3)
4. AI Summaries (Week 4)
5. Production Polish (Week 5)

**Quality Bar**: 9.5+/10 (match Sprint 1 & 2 excellence)

---

## Your Task: Start with Phase 1 (Week 1)

### S3-01: Dashboard Architecture & Setup

**Goal**: Set up React app with routing and API integration

**Technology Stack**:
```
Frontend:
  - React 18 + TypeScript
  - Tailwind CSS (with dark mode support)
  - Recharts (for charts)
  - React Query (API caching)
  - React Router (routing)
  - Vite (build tool)

Backend (already done):
  - FastAPI (Sprint 2)
  - Python 3.11+
```

**Directory Structure**:
```
src/qaagent/dashboard/
  ├── frontend/
  │   ├── src/
  │   │   ├── components/
  │   │   │   ├── Layout/
  │   │   │   │   ├── Header.tsx
  │   │   │   │   ├── Sidebar.tsx
  │   │   │   │   └── ThemeToggle.tsx  ← Dark mode toggle
  │   │   │   ├── Runs/
  │   │   │   ├── Risks/
  │   │   │   ├── Coverage/
  │   │   │   └── Charts/
  │   │   ├── pages/
  │   │   │   ├── Dashboard.tsx
  │   │   │   ├── Runs.tsx
  │   │   │   ├── RunDetails.tsx
  │   │   │   └── Settings.tsx
  │   │   ├── services/
  │   │   │   └── api.ts
  │   │   ├── types/
  │   │   │   └── index.ts
  │   │   ├── App.tsx
  │   │   └── main.tsx
  │   ├── public/
  │   ├── index.html
  │   ├── package.json
  │   ├── tsconfig.json
  │   ├── tailwind.config.js
  │   └── vite.config.ts
  └── README.md
```

**Implementation Steps**:

1. **Create React app with Vite**:
```bash
cd src/qaagent/dashboard
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

2. **Install dependencies**:
```bash
npm install -D tailwindcss postcss autoprefixer
npm install react-router-dom @tanstack/react-query recharts
npm install lucide-react  # Icons
npx tailwindcss init -p
```

3. **Configure Tailwind with dark mode**:
```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',  // ← Enable dark mode with class strategy
  theme: {
    extend: {
      colors: {
        // Custom color scheme
        critical: '#dc2626',  // Red (P0)
        high: '#f59e0b',      // Orange (P1)
        medium: '#fbbf24',    // Yellow (P2)
        low: '#10b981',       // Green (P3)
      },
    },
  },
  plugins: [],
}
```

4. **Create API client**:
```typescript
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class QAAgentAPI {
  private baseURL: string;

  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async getRuns(limit = 50, offset = 0) {
    const response = await fetch(
      `${this.baseURL}/api/runs?limit=${limit}&offset=${offset}`
    );
    if (!response.ok) throw new Error('Failed to fetch runs');
    return response.json();
  }

  async getRun(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}`);
    if (!response.ok) throw new Error('Failed to fetch run');
    return response.json();
  }

  async getRisks(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/risks`);
    if (!response.ok) throw new Error('Failed to fetch risks');
    return response.json();
  }

  async getRecommendations(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/recommendations`);
    if (!response.ok) throw new Error('Failed to fetch recommendations');
    return response.json();
  }

  async getCoverage(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/coverage`);
    if (!response.ok) throw new Error('Failed to fetch coverage');
    return response.json();
  }

  async getFindings(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/findings`);
    if (!response.ok) throw new Error('Failed to fetch findings');
    return response.json();
  }

  async getChurn(runId: string) {
    const response = await fetch(`${this.baseURL}/api/runs/${runId}/churn`);
    if (!response.ok) throw new Error('Failed to fetch churn');
    return response.json();
  }
}

export const api = new QAAgentAPI();
```

5. **Create basic layout with dark mode toggle**:
```typescript
// src/components/Layout/ThemeToggle.tsx
import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Check system preference on mount
    const isDark = localStorage.theme === 'dark' ||
      (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setDarkMode(isDark);
    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  const toggleTheme = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.theme = newDarkMode ? 'dark' : 'light';
    document.documentElement.classList.toggle('dark', newDarkMode);
  };

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
      aria-label="Toggle theme"
    >
      {darkMode ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
```

6. **Setup routing**:
```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Runs } from './pages/Runs';
import { RunDetails } from './pages/RunDetails';
import { Settings } from './pages/Settings';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="runs" element={<Runs />} />
            <Route path="runs/:runId" element={<RunDetails />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

7. **Create .env.example**:
```bash
# .env.example
VITE_API_URL=http://localhost:8000
```

**Acceptance Criteria**:
- [ ] React app scaffolded with Vite
- [ ] TypeScript configured
- [ ] Tailwind CSS integrated with dark mode
- [ ] API client service working
- [ ] Basic routing (Dashboard, Runs, Settings)
- [ ] Dark mode toggle functional
- [ ] Can run `npm run dev` and see app
- [ ] Can fetch runs from API (http://localhost:8000)

**Testing**:
```bash
# Terminal 1: Start API server
qaagent api

# Terminal 2: Start React dev server
cd src/qaagent/dashboard/frontend
npm run dev

# Open browser: http://localhost:5173
# Toggle dark mode - should work
# Navigate between routes - should work
```

---

### S3-02: Dashboard Overview Page

**Goal**: Main dashboard showing key metrics at a glance

**Design** (Light Mode):
```
┌─────────────────────────────────────────────────────┐
│  QA Agent                    🌙 [Settings]          │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────────────────────────────────┐   │
│  │  📊 Overview                                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 42 Runs  │  │ 18 P0/P1 │  │ 65% Avg  │          │
│  │ Total    │  │ Risks    │  │ Coverage │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                       │
│  ┌─────────────────────────────────────────────┐   │
│  │ Top Risks (Latest Run)         [View All →] │   │
│  ├─────────────────────────────────────────────┤   │
│  │ 🔴 P0  src/auth/login.py       Score: 85.0 │   │
│  │ 🟠 P1  src/api/users.py        Score: 72.0 │   │
│  │ 🟡 P2  src/services/payment.py Score: 58.0 │   │
│  └─────────────────────────────────────────────┘   │
│                                                       │
│  ┌─────────────────────────────────────────────┐   │
│  │ Coverage Gaps (CUJs)           [View All →] │   │
│  ├─────────────────────────────────────────────┤   │
│  │ ⚠️  Login Flow      45% ████░░░░  (▼35%)   │   │
│  │ ⚠️  Payment         52% █████░░░  (▼18%)   │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Components to Create**:

1. **MetricCard.tsx**:
```typescript
interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
}

export function MetricCard({ title, value, icon, trend }: MetricCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {value}
          </p>
        </div>
        {icon && (
          <div className="text-blue-500 dark:text-blue-400">
            {icon}
          </div>
        )}
      </div>
      {trend && (
        <div className="mt-2 text-sm">
          {trend === 'up' && <span className="text-green-600">↗ Improving</span>}
          {trend === 'down' && <span className="text-red-600">↘ Declining</span>}
        </div>
      )}
    </div>
  );
}
```

2. **TopRisksTable.tsx**:
```typescript
interface Risk {
  risk_id: string;
  component: string;
  score: number;
  band: string;
  severity: string;
}

export function TopRisksTable({ risks }: { risks: Risk[] }) {
  const getBandColor = (band: string) => {
    switch (band) {
      case 'P0': return 'text-critical dark:text-red-400';
      case 'P1': return 'text-high dark:text-orange-400';
      case 'P2': return 'text-medium dark:text-yellow-400';
      default: return 'text-low dark:text-green-400';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Top Risks (Latest Run)
        </h2>
        <a href="/runs" className="text-blue-600 dark:text-blue-400 text-sm hover:underline">
          View All →
        </a>
      </div>
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {risks.slice(0, 5).map(risk => (
          <div key={risk.risk_id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className={`font-bold ${getBandColor(risk.band)}`}>
                  {risk.band === 'P0' && '🔴'}
                  {risk.band === 'P1' && '🟠'}
                  {risk.band === 'P2' && '🟡'}
                  {risk.band === 'P3' && '🟢'}
                  {' '}{risk.band}
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {risk.component}
                </span>
              </div>
              <span className="text-gray-600 dark:text-gray-400">
                Score: {risk.score.toFixed(1)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

3. **Dashboard.tsx** (main page):
```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { MetricCard } from '../components/MetricCard';
import { TopRisksTable } from '../components/TopRisksTable';
import { Activity, AlertCircle, CheckCircle } from 'lucide-react';

export function Dashboard() {
  const { data: runs } = useQuery({
    queryKey: ['runs'],
    queryFn: () => api.getRuns(10, 0)
  });

  const latestRun = runs?.runs[0];

  const { data: risks } = useQuery({
    queryKey: ['risks', latestRun?.run_id],
    queryFn: () => api.getRisks(latestRun.run_id),
    enabled: !!latestRun
  });

  const { data: coverage } = useQuery({
    queryKey: ['coverage', latestRun?.run_id],
    queryFn: () => api.getCoverage(latestRun.run_id),
    enabled: !!latestRun
  });

  // Calculate metrics
  const totalRuns = runs?.total || 0;
  const highPriorityRisks = risks?.risks.filter(r => r.band === 'P0' || r.band === 'P1').length || 0;
  const avgCoverage = coverage?.coverage.length > 0
    ? (coverage.coverage.reduce((sum, c) => sum + c.value, 0) / coverage.coverage.length * 100).toFixed(0)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Overview of your QA analysis
        </p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Total Runs"
          value={totalRuns}
          icon={<Activity size={32} />}
        />
        <MetricCard
          title="P0/P1 Risks"
          value={highPriorityRisks}
          icon={<AlertCircle size={32} />}
        />
        <MetricCard
          title="Avg Coverage"
          value={`${avgCoverage}%`}
          icon={<CheckCircle size={32} />}
        />
      </div>

      {/* Top Risks */}
      <TopRisksTable risks={risks?.risks || []} />

      {/* Loading states */}
      {!latestRun && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-blue-800 dark:text-blue-200">
            No runs found. Run your first analysis with: <code className="bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded">qaagent analyze collectors</code>
          </p>
        </div>
      )}
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Dashboard shows metrics (runs, risks, coverage)
- [ ] Top 5 risks displayed with severity badges
- [ ] Empty state if no runs
- [ ] Dark mode styling looks good
- [ ] Responsive on mobile
- [ ] Loading states while fetching data

---

### S3-03: Runs List & Details Pages

**Goal**: Browse runs and view details

**Implementation**: See SPRINT3_PLAN.md S3-03 for full specs

**Key Features**:
- Runs list with search
- Pagination
- Run details with tabs
- Click risk → navigate to details

---

### S3-04: Risks View with Drill-Down

**Goal**: Interactive risks table

**Implementation**: See SPRINT3_PLAN.md S3-04 for full specs

**Key Features**:
- Sortable/filterable table
- Expandable rows
- Factor breakdown visualization
- Evidence linking

---

## Development Workflow

### Starting Development

```bash
# Terminal 1: Start API server
cd /Users/jackblacketter/projects/qaagent
qaagent api

# Terminal 2: Start React dev server
cd src/qaagent/dashboard/frontend
npm run dev

# Browser: http://localhost:5173
```

### Testing Changes

1. Make changes to React components
2. Hot reload updates automatically
3. Test in browser (toggle dark mode, navigate routes)
4. Ensure API calls work
5. Test responsive design (mobile view)

### Checkpoint

After completing S3-01 through S3-04:
1. Run `npm run build` to ensure production build works
2. Test all routes
3. Test dark mode
4. Take screenshots
5. Hand back to Claude for review

---

## Important Notes

### Dark Mode Implementation

**Use Tailwind's dark: prefix everywhere**:
```typescript
// ✅ Good
<div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">

// ❌ Bad
<div className="bg-white text-gray-900">
```

**Color palette**:
```
Light Mode               Dark Mode
bg-white                 dark:bg-gray-800
bg-gray-50              dark:bg-gray-900
text-gray-900           dark:text-white
text-gray-600           dark:text-gray-400
border-gray-200         dark:border-gray-700
```

### API Integration

**Always use React Query**:
```typescript
// ✅ Good - with caching
const { data, isLoading, error } = useQuery({
  queryKey: ['risks', runId],
  queryFn: () => api.getRisks(runId)
});

// ❌ Bad - no caching
const [data, setData] = useState(null);
useEffect(() => {
  api.getRisks(runId).then(setData);
}, [runId]);
```

### Error Handling

**Always handle errors gracefully**:
```typescript
if (error) {
  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
      <p className="text-red-800 dark:text-red-200">
        Failed to load data: {error.message}
      </p>
    </div>
  );
}
```

### Loading States

**Use skeleton screens**:
```typescript
if (isLoading) {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mt-2"></div>
    </div>
  );
}
```

---

## Quality Checklist

Before checkpoint, ensure:

- [ ] **TypeScript**: No `any` types, all props typed
- [ ] **Dark mode**: All components support dark mode
- [ ] **Responsive**: Works on mobile (375px) to desktop (1920px)
- [ ] **Accessibility**: ARIA labels, keyboard navigation
- [ ] **Loading states**: Skeleton screens while loading
- [ ] **Error states**: Graceful error messages
- [ ] **Empty states**: Helpful messages when no data
- [ ] **Performance**: No unnecessary re-renders
- [ ] **Code quality**: Clean, readable, commented where needed
- [ ] **Tests**: Can run `npm run build` successfully

---

## Reference Documents

**Full Sprint 3 Plan**: `handoff/SPRINT3_PLAN.md`
**Sprint 3 Summary**: `handoff/SPRINT3_SUMMARY.md`
**Sprint 2 API**: API is already running, see Sprint 2 docs

---

## Questions During Development

If you encounter:
- **Design questions** → Use your judgment, prioritize usability
- **Technical blockers** → Document and ask Claude at checkpoint
- **Scope questions** → Refer to SPRINT3_PLAN.md, stay focused on Phase 1

---

## Success Criteria (Phase 1)

**You're done with Phase 1 when**:
- [ ] React app runs with `npm run dev`
- [ ] Dark mode toggle works perfectly
- [ ] Dashboard shows real data from API
- [ ] Runs list shows all runs with search
- [ ] Run details page shows all evidence types
- [ ] Risks view has sortable table with drill-down
- [ ] Everything looks good in both light and dark mode
- [ ] Mobile responsive
- [ ] No TypeScript errors
- [ ] Production build works

**Then**: Pause, hand to Claude for Checkpoint 1 review

---

## Let's Build! 🚀

You have everything you need to start Phase 1. Focus on:
1. Quality over speed (5 weeks is fine)
2. Dark mode support in all components
3. Clean, maintainable React code
4. Match Sprint 1 & 2 excellence (9.5+/10)

**Good luck, Codex! Create something beautiful.** ✨
