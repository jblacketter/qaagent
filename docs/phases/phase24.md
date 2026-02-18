# Phase 24: Doc Page — Wire Up Existing Components

## Status: Complete

## Summary

Wired pre-built but unused UI components into the App Documentation page (`/doc`):

1. **StalenessBar** — Shows doc freshness (Fresh/Aging/Stale) at the top of the page with an auto-regenerate button. Fixed bug where `repoId` was not passed to the regenerate API call.

2. **Architecture Diagrams** — Tabbed section with three interactive React Flow diagrams:
   - Feature Map (nodes with type `feature`)
   - Integration Map (nodes with type `feature` + `integration`)
   - Route Graph (nodes with type `route_group`)
   - Nodes/edges filtered from `doc.architecture_nodes` and `doc.architecture_edges`.

3. **All Routes Table** — Collapsible section aggregating routes from all features into a single `RouteTable`. Shows total count in header, expands on click.

## Files Changed

| File | Change |
|------|--------|
| `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` | Added StalenessBar, Architecture tabs, RouteTable |
| `src/qaagent/dashboard/frontend/src/components/Doc/StalenessBar.tsx` | Added `repoId` prop, fixed `regenerateDoc` and `queryKey` |

No backend changes — all data already flowed through existing API endpoints.
