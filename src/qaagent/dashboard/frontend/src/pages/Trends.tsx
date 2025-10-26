import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { CoverageTrendChart } from "../components/Charts/CoverageTrendChart";
import { RiskBandTrendChart } from "../components/Charts/RiskBandTrendChart";
import { AverageRiskScoreChart } from "../components/Charts/AverageRiskScoreChart";
import { HighRiskCountChart } from "../components/Charts/HighRiskCountChart";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import { ExportMenu } from "../components/ui/ExportMenu";
import { exportDataAsCSV, exportDataAsJSON, flattenForCSV } from "../utils/export";

export function TrendsPage() {
  const trendsQuery = useQuery({
    queryKey: ["runs", "trends", 20],
    queryFn: () => apiClient.getRunTrends(20),
  });

  const trendData = trendsQuery.data?.trend ?? [];
  const isLoading = trendsQuery.isLoading;
  const isError = trendsQuery.isError;

  const summary = useMemo(() => {
    if (!trendData.length) {
      return {
        totalRuns: trendsQuery.data?.total ?? 0,
        latestRun: null as string | null,
      };
    }
    const latest = trendData[trendData.length - 1];
    return {
      totalRuns: trendsQuery.data?.total ?? trendData.length,
      latestRun: latest.run_id,
    };
  }, [trendData, trendsQuery.data?.total]);

  const handleExportCSV = () => {
    const flatData = flattenForCSV(trendData);
    exportDataAsCSV(flatData, "qa-agent-trends");
  };

  const handleExportJSON = () => {
    exportDataAsJSON(
      {
        trends: trendData,
        summary: {
          totalRuns: summary.totalRuns,
          latestRun: summary.latestRun,
        },
      },
      "qa-agent-trends"
    );
  };

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold">Quality Trends</h1>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Track how risk and coverage evolve across analysis runs. Add more runs with `qaagent analyze collectors` and
                  `qaagent analyze risks` to keep this data fresh.
                </p>
              </div>
              <ExportMenu
                onExportCSV={handleExportCSV}
                onExportJSON={handleExportJSON}
                disabled={isLoading}
              />
            </div>
            <dl className="mt-4 grid gap-4 text-xs sm:grid-cols-2 md:grid-cols-4">
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Runs indexed</dt>
                <dd className="text-base font-semibold text-slate-800 dark:text-slate-200">{summary.totalRuns}</dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Latest run</dt>
                <dd className="text-base font-semibold text-slate-800 dark:text-slate-200">{summary.latestRun ?? "–"}</dd>
              </div>
            </dl>
          </>
        )}
      </section>

      {isError && <Alert variant="error">Failed to load trend data. Ensure previous analyses exist and the API is reachable.</Alert>}

      <section className="grid gap-4 xl:grid-cols-2">
        <ChartPanel
          title="Coverage trend"
          description="Average component coverage per run"
          loading={isLoading}
          isEmpty={!trendData.length}
          error={isError ? "Unable to load coverage trends." : undefined}
          skeleton={<Skeleton className="h-64 w-full" />}
        >
          <CoverageTrendChart data={trendData.map((point) => ({
            runId: point.run_id,
            createdAt: point.created_at,
            averageCoverage: point.average_coverage,
            highRiskCount: point.high_risk_count,
          }))}
          />
        </ChartPanel>

        <ChartPanel
          title="Risk band mix"
          description="Stacked counts of P0–P3 risks over time"
          loading={isLoading}
          isEmpty={!trendData.length}
          error={isError ? "Unable to load risk band trends." : undefined}
          skeleton={<Skeleton className="h-64 w-full" />}
        >
          <RiskBandTrendChart data={trendData} />
        </ChartPanel>
      </section>

      <section className="grid gap-4 xl:grid-cols-[2fr,1fr]">
        <ChartPanel
          title="Average risk score"
          description="Mean risk score across all components"
          loading={isLoading}
          isEmpty={!trendData.some((point) => point.average_risk_score !== null)}
          error={isError ? "Unable to load average risk score trend." : undefined}
          skeleton={<Skeleton className="h-64 w-full" />}
        >
          <AverageRiskScoreChart data={trendData} />
        </ChartPanel>

        <ChartPanel
          title="High-risk counts"
          description="Combined P0 + P1 risks"
          loading={isLoading}
          isEmpty={!trendData.length}
          error={isError ? "Unable to load high-risk counts." : undefined}
          skeleton={<Skeleton className="h-64 w-full" />}
        >
          <HighRiskCountChart data={trendData} />
        </ChartPanel>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-base font-semibold">Run snapshot</h2>
        {isError ? (
          <Alert variant="error">Trend data is unavailable.</Alert>
        ) : isLoading ? (
          <div className="mt-3 space-y-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : !trendData.length ? (
          <Alert variant="info">No trend data yet. Generate multiple runs to populate this table.</Alert>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
              <thead className="bg-slate-50 dark:bg-slate-900/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Run ID</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Created</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Avg coverage</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">High risks</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-500 dark:text-slate-400">Avg risk score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {trendData.map((point) => (
                  <tr key={point.run_id}>
                    <td className="px-3 py-2 text-slate-700 dark:text-slate-200">{point.run_id}</td>
                    <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                      {new Date(point.created_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                      {point.average_coverage !== null ? `${Math.round(point.average_coverage * 100)}%` : "–"}
                    </td>
                    <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{point.high_risk_count}</td>
                    <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                      {point.average_risk_score !== null ? point.average_risk_score.toFixed(1) : "–"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

interface ChartPanelProps {
  title: string;
  description?: string;
  loading: boolean;
  isEmpty: boolean;
  children: ReactNode;
  error?: string;
  skeleton?: ReactNode;
}

function ChartPanel({ title, description, loading, isEmpty, children, error, skeleton }: ChartPanelProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="mb-3 space-y-1">
        <h2 className="text-base font-semibold">{title}</h2>
        {description ? <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p> : null}
      </header>
      {error ? (
        <Alert variant="error">{error}</Alert>
      ) : loading ? (
        skeleton ?? <Skeleton className="h-56 w-full" />
      ) : isEmpty ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No data available yet.</p>
      ) : (
        children
      )}
    </section>
  );
}
