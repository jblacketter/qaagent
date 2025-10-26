# QA Agent Dashboard Frontend

This package contains the React-based dashboard that consumes the QA Agent API. It is organized as a standalone Vite + React + TypeScript project with Tailwind CSS, React Query, React Router, and Recharts.

## Getting Started

```bash
cd src/qaagent/dashboard/frontend
npm install
npm run dev
```

The dashboard expects the QA Agent API (Sprint 2) to be running locally:

```bash
qaagent api --runs-dir ~/.qaagent/runs
```

Set a custom API base URL by creating a `.env` file inside `frontend/`:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Build for Production

```bash
npm run build
npm run preview
```

For production deployments, serve the `dist/` directory with your preferred static file server. A lightweight helper `server.py` will be provided in later phases to serve the built assets via FastAPI.

## Project Structure

- `src/components/` – Layout primitives (header, sidebar, theme toggle) and reusable UI blocks
- `src/pages/` – High-level views (landing, repository setup, dashboard, runs, risks, settings)
- `src/services/api.ts` – Minimal client wrapping the QA Agent REST API
- `src/types/` – Shared TypeScript interfaces for API payloads

Tailwind is configured with `darkMode: 'class'`, providing a theme toggle that stores preferences in `localStorage`.

## User Workflow

The dashboard follows a repository-centric workflow:

1. **Landing Page** (`/`) - Overview of features with quick access to repositories
2. **Repository Setup** (`/setup`) - Add new repositories (local or GitHub) with analysis options
3. **Repositories List** (`/repositories`) - Manage all repositories, trigger re-scans, view dashboards
4. **Dashboard** (`/dashboard?repo=X`) - Per-repository metrics, risk overview, and quality trends
5. **Risks Explorer** (`/risks?run=X&risk=Y`) - Deep dive into risks with:
   - Collapsible severity sections (Critical → High → Medium → Low)
   - Detailed risk explanations with specific security issues to investigate
   - Actionable recommendations with tools to run and next steps
   - Filtered to show application code only (vendor libraries excluded)

## Key Features

- **Repository Management** - Add, configure, and analyze multiple repositories
- **Risk Prioritization** - Risks grouped by severity and sorted by score
- **Actionable Insights** - Specific guidance on what to investigate and how to fix issues
- **Critical User Journey Coverage** - Track test coverage across key user workflows
- **Dark Mode Support** - Theme preferences stored in localStorage
- **Real-time Updates** - React Query for efficient data fetching and caching

## Roadmap

Sprint 3 Phase 2 and beyond will add:
- Rich visualizations (Recharts)
- Comparative run analysis
- PDF/HTML exports and AI summaries
- Persistent repository storage (currently in-memory)

Contributions welcome! Submit issues or PRs to improve the dashboard experience.
