import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { CujCoverageRadial } from "../components/Charts/CujCoverageRadial";
import { CoverageBar } from "../components/ui/CoverageBar";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import { ExportMenu } from "../components/ui/ExportMenu";
import { exportDataAsCSV, exportDataAsJSON, flattenForCSV } from "../utils/export";

export function CujCoveragePage() {
  const runsQuery = useQuery({
    queryKey: ["runs", { limit: 1 }],
    queryFn: () => apiClient.getRuns(1, 0),
  });

  const latestRun = runsQuery.data?.runs[0];
  const latestRunId = latestRun?.run_id;

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

  const isLoading = runsQuery.isLoading || cujQuery.isLoading || coverageQuery.isLoading;
  const hasError = runsQuery.isError || cujQuery.isError || coverageQuery.isError;

  const cujGroups = useMemo(() => {
    const cujs = cujQuery.data ?? [];
    if (!cujs.length) {
      return [] as Array<{
        id: string;
        name: string;
        coverage: number;
        target: number;
        components: Array<{ component: string; coverage: number }>;
      }>;
    }

    return cujs.map((cuj) => {
      const componentDetails = cuj.components.map((component) => ({
        component: component.component,
        coverage: component.coverage,
      }));
      const avgCoverage = componentDetails.length
        ? componentDetails.reduce((acc, item) => acc + item.coverage, 0) / componentDetails.length
        : 0;

      return {
        id: cuj.id,
        name: cuj.name,
        coverage: cuj.coverage,
        target: cuj.target,
        components: componentDetails,
        avgCoverage,
      };
    });
  }, [cujQuery.data]);

  const handleExportCSV = () => {
    const flatData = cujGroups.flatMap((cuj) =>
      cuj.components.map((comp) => ({
        cuj_id: cuj.id,
        cuj_name: cuj.name,
        cuj_coverage: cuj.coverage,
        cuj_target: cuj.target,
        component: comp.component,
        component_coverage: comp.coverage,
      }))
    );
    exportDataAsCSV(flatData, "qa-agent-cuj-coverage");
  };

  const handleExportJSON = () => {
    exportDataAsJSON(
      {
        run_id: latestRunId,
        cuj_coverage: cujGroups,
        total_cujs: cujGroups.length,
      },
      "qa-agent-cuj-coverage"
    );
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">CUJ Coverage</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Track test coverage across critical user journeys to ensure end-to-end quality.
            </p>
            {latestRun && (
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Latest run: <span className="font-medium text-slate-600 dark:text-slate-300">{latestRun.run_id}</span> on
                {" "}
                {new Date(latestRun.created_at).toLocaleString()} for {latestRun.target.name}
              </p>
            )}
          </div>
          <ExportMenu
            onExportCSV={handleExportCSV}
            onExportJSON={handleExportJSON}
            disabled={isLoading}
          />
        </div>
      </section>

      {hasError && (
        <Alert variant="error">Failed to load CUJ coverage data. Please refresh or rerun the latest analysis.</Alert>
      )}

      {!isLoading && !latestRunId && !hasError && (
        <section className="rounded-lg border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
          <p className="text-slate-500 dark:text-slate-400">
            No analysis runs found. Run <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">qaagent analyze collectors</code>{" "}
            and then <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">qaagent analyze risks</code> to populate CUJ coverage.
          </p>
        </section>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Coverage Overview</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Gauge which journeys are above or below their target coverage.
            </p>
          </div>
        </header>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <CujCoverageRadial data={cujQuery.data ?? []} />
        )}
      </section>

      {isLoading && (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
            >
              <Skeleton className="h-5 w-32" />
              <Skeleton className="mt-3 h-3 w-full" />
              <div className="mt-4 space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && !hasError && cujGroups.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {cujGroups.map((cuj) => (
            <section
              key={cuj.id}
              className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{cuj.name}</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Target {Math.round(cuj.target * 100)}% • Actual {Math.round((cuj.coverage ?? cuj.avgCoverage) * 100)}%
                  </p>
                </div>
                <span
                  className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  aria-label={`Gap ${Math.max(0, Math.round((cuj.target - (cuj.coverage ?? cuj.avgCoverage)) * 100))}%`}
                >
                  Gap {Math.max(0, Math.round((cuj.target - (cuj.coverage ?? cuj.avgCoverage)) * 100))}%
                </span>
              </div>

              <div className="mt-4">
                <CoverageBar value={cuj.coverage ?? cuj.avgCoverage} target={cuj.target} />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Average coverage across {cuj.components.length} mapped components.
                </p>
              </div>

              <div className="mt-5 space-y-2">
                <h4 className="text-sm font-medium text-slate-600 dark:text-slate-400">Components</h4>
                {cuj.components.map((component) => (
                  <div
                    key={component.component}
                    className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800/60"
                  >
                    <span className="truncate text-slate-700 dark:text-slate-200" title={component.component}>
                      {component.component}
                    </span>
                    <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                      {Math.round(component.coverage * 100)}%
                    </span>
                  </div>
                ))}
                {!cuj.components.length && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    No components mapped to this journey. Update <code className="rounded bg-slate-100 px-1 py-0.5 dark:bg-slate-800">cuj.yaml</code> to add mappings.
                  </p>
                )}
              </div>

              {cuj.target > (cuj.coverage ?? cuj.avgCoverage) && (
                <div className="mt-4 rounded-md border border-orange-200 bg-orange-50 p-3 text-xs text-orange-700 dark:border-orange-900/50 dark:bg-orange-900/20 dark:text-orange-200">
                  Coverage is below target. Prioritize additional tests for this journey.
                </div>
              )}
            </section>
          ))}
        </div>
      )}

      {!isLoading && !hasError && cujGroups.length === 0 && latestRunId && (
        <section className="rounded-lg border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
          <p className="text-slate-500 dark:text-slate-400">
            No CUJ coverage was derived from the latest run. Define journeys in your <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">cuj.yaml</code>
            {" "}or rerun analysis to populate this view.
          </p>
        </section>
      )}
    </div>
  );
}
