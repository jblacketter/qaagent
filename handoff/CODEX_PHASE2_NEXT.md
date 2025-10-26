# Handoff to Codex: Sprint 3 Phase 2 - Next Tasks

**Date**: 2025-10-25
**From**: Claude (after Phase 1 success + user testing)
**To**: Codex
**Status**: Ready to implement
**Current Progress**: Phase 1 complete (9.5/10), Phase 2 ~70% complete

---

## Excellent Work So Far! 🌟

**What you delivered**:
- ✅ Phase 1 color enhancements (RiskBadge, CoverageBar, MetricCard) - Perfect!
- ✅ 8 chart components with Recharts - Bonus!
- ✅ Trends page with multiple visualizations - Bonus!
- ✅ API `/runs/trends` endpoint - Working!
- ✅ Real data integration - Tested with sonicgrid project!

**User feedback after testing**:
> "ok we have coverage data now" ✅

**Quality**: 9.5/10 - Exceeded expectations!

---

## What's Next: Phase 2 Completion

You've already done the hard parts (charts, trends, API). Now let's finish Phase 2 polish:

### Remaining Phase 2 Tasks

**Priority Order**:

1. **S3-06: CUJ (Critical User Journey) Coverage Views** - NEW
2. **S3-08: Mobile Responsive Polish** - Refinements
3. **Minor Bug Fix**: Route ordering issue (already fixed by me)

Then move to **Phase 3: Reports & Export** (PDF generation, exports, etc.)

---

## Task 1: CUJ Coverage Views (S3-06)

**Goal**: Allow users to see test coverage grouped by Critical User Journeys (CUJs)

**Background**: Users define CUJs in a `cuj.yaml` file that maps components to user flows like:
- Login Flow
- Checkout Flow
- Settings Management

The dashboard should show coverage **per CUJ** instead of just per component.

---

### Implementation Plan

#### 1. Create CUJ Coverage Page

**New file**: `src/pages/CujCoverage.tsx`

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../services/api";
import { CujCoverageRadial } from "../components/Charts/CujCoverageRadial";
import { CoverageBar } from "../components/ui/CoverageBar";

export function CujCoveragePage() {
  const runsQuery = useQuery({
    queryKey: ["runs", { limit: 1 }],
    queryFn: () => apiClient.getRuns(1, 0),
  });

  const latestRunId = runsQuery.data?.runs[0]?.run_id;

  const cujQuery = useQuery({
    queryKey: ["cuj", latestRunId],
    queryFn: () => (latestRunId ? apiClient.getCujCoverage(latestRunId) : Promise.resolve([])),
    enabled: Boolean(latestRunId),
  });

  const coverageQuery = useQuery({
    queryKey: ["coverage", latestRunId],
    queryFn: () => (latestRunId ? apiClient.getCoverage(latestRunId) : Promise.resolve([])),
    enabled: Boolean(latestRunId),
  });

  // Group components by CUJ
  const cujGroups = useMemo(() => {
    const cujs = cujQuery.data ?? [];
    const coverage = coverageQuery.data ?? [];

    // Create map of component -> coverage
    const coverageMap = new Map(
      coverage.map(c => [c.component, c.value])
    );

    // Group by CUJ and calculate average coverage
    return cujs.map(cuj => ({
      name: cuj.name,
      components: cuj.components,
      avgCoverage: cuj.components.reduce((acc, comp) => {
        return acc + (coverageMap.get(comp) ?? 0);
      }, 0) / cuj.components.length,
      componentDetails: cuj.components.map(comp => ({
        name: comp,
        coverage: coverageMap.get(comp) ?? 0,
      })),
    }));
  }, [cujQuery.data, coverageQuery.data]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <section>
        <h1 className="text-2xl font-bold">CUJ Coverage</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Test coverage grouped by Critical User Journeys
        </p>
      </section>

      {/* Overview Chart */}
      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold mb-4">Coverage Overview</h2>
        <CujCoverageRadial data={cujQuery.data ?? []} />
      </section>

      {/* Per-CUJ Details */}
      <div className="grid gap-4 lg:grid-cols-2">
        {cujGroups.map((cuj) => (
          <section
            key={cuj.name}
            className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="mb-4">
              <h3 className="text-base font-semibold">{cuj.name}</h3>
              <div className="mt-2">
                <CoverageBar value={cuj.avgCoverage} />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {Math.round(cuj.avgCoverage * 100)}% average coverage across {cuj.components.length} components
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-slate-600 dark:text-slate-400">Components</h4>
              {cuj.componentDetails.map((comp) => (
                <div
                  key={comp.name}
                  className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/50"
                >
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
                    {comp.name}
                  </span>
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 ml-2">
                    {Math.round(comp.coverage * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Empty State */}
      {!cujGroups.length && (
        <section className="rounded-lg border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
          <p className="text-slate-500 dark:text-slate-400">
            No CUJ data available. Create a <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">cuj.yaml</code> file to define Critical User Journeys.
          </p>
        </section>
      )}
    </div>
  );
}
```

#### 2. Add Route for CUJ Page

**File**: `src/App.tsx`

Add the route:
```typescript
<Route path="/cuj" element={<CujCoveragePage />} />
```

#### 3. Add Sidebar Link

**File**: `src/components/Layout/Sidebar.tsx`

Add to links array:
```typescript
{ to: "/cuj", label: "CUJ Coverage", icon: Target }, // Import Target from lucide-react
```

#### 4. API Client Method

**File**: `src/services/api.ts`

Add method (if not already there):
```typescript
async getCujCoverage(runId: string): Promise<CujRecord[]> {
  const response = await fetch(`${this.baseUrl}/api/runs/${runId}/cuj`);
  if (!response.ok) {
    throw new Error('Failed to fetch CUJ coverage');
  }
  return response.json();
}
```

**Type**: Add to `src/types/index.ts`:
```typescript
export interface CujRecord {
  cuj_id: string;
  name: string;
  components: string[];
  coverage?: number;
}
```

---

## Task 2: Mobile Responsive Polish (S3-08)

**Goal**: Ensure dashboard works well on mobile devices (375px - 768px width)

### What to Check & Fix

#### 1. Navigation on Mobile

**Current**: Sidebar is hidden on mobile (`md:flex`)
**Fix**: Add hamburger menu for mobile

**File**: `src/components/Layout/Header.tsx`

```typescript
import { Menu } from 'lucide-react';
import { useState } from 'react';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Menu size={20} />
          </button>

          <div>
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">QA Agent Dashboard</h1>
            <p className="hidden sm:block text-sm text-slate-500 dark:text-slate-400">
              Quality insights and risk prioritization at a glance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/settings" className="...">Settings</Link>
          <ThemeToggle />
        </div>
      </header>

      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        >
          <aside
            className="fixed left-0 top-0 h-full w-64 bg-white dark:bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <Sidebar onLinkClick={() => setMobileMenuOpen(false)} />
          </aside>
        </div>
      )}
    </>
  );
}
```

**Update Sidebar**: Add `onLinkClick` prop to close mobile menu when navigating

#### 2. Chart Responsiveness

**File**: All chart components

Ensure all charts use `ResponsiveContainer` from Recharts (you already do this ✅)

Test on mobile:
- Charts should scale properly
- Tooltips should work on touch
- No horizontal scrolling

#### 3. Table Overflow

**Files**: `Trends.tsx`, `Risks.tsx`, `RunDetails.tsx`

Wrap tables in scrollable container:
```typescript
<div className="overflow-x-auto">
  <table className="min-w-full">
    {/* ... */}
  </table>
</div>
```

#### 4. Metric Card Grid

**File**: `Dashboard.tsx`

Current grid is good, but verify on mobile:
```typescript
<section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
  {/* Metric cards - should be 1 col on mobile, 2 on tablet, 4 on desktop */}
</section>
```

#### 5. Touch Targets

Ensure all interactive elements are **at least 44px tall** (Apple's guideline):
- Buttons
- Links
- Chart hover areas

---

## Task 3: Minor Improvements

### A. Loading Skeletons

Instead of "Loading...", show skeleton placeholders:

```typescript
function CardSkeleton() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 animate-pulse">
      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-24 mb-2"></div>
      <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-16 mb-1"></div>
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-32"></div>
    </div>
  );
}
```

Use in Dashboard:
```typescript
{runsQuery.isLoading ? <CardSkeleton /> : <MetricCard ... />}
```

### B. Error States

Add better error handling:

```typescript
{runsQuery.isError && (
  <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
    <p className="text-sm text-red-800 dark:text-red-200">
      Failed to load data. Please try refreshing the page.
    </p>
  </div>
)}
```

### C. Accessibility

Add ARIA labels:
```typescript
<button aria-label="Toggle theme" onClick={toggleTheme}>
  {darkMode ? <Sun /> : <Moon />}
</button>
```

---

## Testing Checklist

Before marking complete, test:

### Desktop (1920px)
- [ ] All charts display correctly
- [ ] No horizontal scrolling
- [ ] Sidebar navigation works
- [ ] All colors visible in light mode
- [ ] All colors visible in dark mode

### Tablet (768px)
- [ ] 2-column grid layouts work
- [ ] Charts scale properly
- [ ] Tables scroll horizontally if needed
- [ ] Touch targets are adequate

### Mobile (375px)
- [ ] Mobile menu opens/closes
- [ ] Single column layouts
- [ ] No text cutoff
- [ ] Charts are readable
- [ ] Coverage bars display properly
- [ ] Risk badges fit properly

### Functionality
- [ ] CUJ page shows data (if cuj.yaml exists)
- [ ] CUJ page shows empty state (if no cuj.yaml)
- [ ] All navigation links work
- [ ] Dark mode persists across pages
- [ ] Loading states show properly
- [ ] Error states show helpful messages

---

## Expected Timeline

**Estimated time**: 4-6 hours

- CUJ Coverage page: 2-3 hours
- Mobile responsive polish: 1.5 hours
- Loading/error states: 30 min
- Testing all breakpoints: 1 hour

---

## After Phase 2

Once this is complete, we'll move to **Phase 3: Reports & Export**:
- PDF report generation
- Executive summaries
- Technical reports
- CSV/JSON exports

---

## Questions?

If anything is unclear:

1. **CUJ data structure**: Check the API endpoint `/api/runs/{run_id}/cuj` for the actual response format
2. **Mobile breakpoints**: Use Tailwind's standard breakpoints (sm: 640px, md: 768px, lg: 1024px, xl: 1280px)
3. **Chart sizing**: Recharts ResponsiveContainer handles most of this automatically
4. **Icons**: Use lucide-react (already in dependencies)

---

**You're doing excellent work!** The dashboard looks professional and performs well. These final Phase 2 tasks will make it production-ready.

Good luck! 🚀
