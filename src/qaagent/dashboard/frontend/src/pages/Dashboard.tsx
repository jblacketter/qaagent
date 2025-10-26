import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Activity, AlertCircle, LineChart, ShieldCheck } from "lucide-react";

import { apiClient } from "../services/api";
import { MetricCard } from "../components/ui/MetricCard";
import { RiskBadge } from "../components/ui/RiskBadge";
import { CoverageBar } from "../components/ui/CoverageBar";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import { RiskDistributionChart } from "../components/Charts/RiskDistributionChart";
import { RiskFactorsChart } from "../components/Charts/RiskFactorsChart";
import { RiskHeatmap } from "../components/Charts/RiskHeatmap";
import { CoverageTrendChart } from "../components/Charts/CoverageTrendChart";
import { CujCoverageRadial } from "../components/Charts/CujCoverageRadial";
import { ExportMenu } from "../components/ui/ExportMenu";
import { exportDataAsCSV, exportDataAsJSON } from "../utils/export";

export function DashboardPage() {
  const [reportDialogOpen, setReportDialogOpen] = useState(false);

  const runsQuery = useQuery({
    queryKey: ["runs", { limit: 6 }],
    queryFn: () => apiClient.getRuns(6, 0),
  });

  const latestRunId = runsQuery.data?.runs[0]?.run_id;

  const risksQuery = useQuery({
    queryKey: ["dashboard", "risks", latestRunId],
    queryFn: () => (latestRunId ? apiClient.getRisks(latestRunId) : Promise.resolve([])),
    enabled: Boolean(latestRunId),
  });

  const coverageQuery = useQuery({
    queryKey: ["dashboard", "coverage", latestRunId],
    queryFn: () => (latestRunId ? apiClient.getCoverage(latestRunId) : Promise.resolve([])),
    enabled: Boolean(latestRunId),
  });

  const recommendationsQuery = useQuery({
    queryKey: ["dashboard", "recommendations", latestRunId],
    queryFn: () => (latestRunId ? apiClient.getRecommendations(latestRunId) : Promise.resolve([])),
    enabled: Boolean(latestRunId),
  });

  const cujCoverageQuery = useQuery({
    queryKey: ["dashboard", "cuj", latestRunId],
    queryFn: () => (latestRunId ? apiClient.getCujCoverage(latestRunId) : Promise.resolve([])),
    enabled: Boolean(latestRunId),
  });

  const trendsQuery = useQuery({
    queryKey: ["dashboard", "trends"],
    queryFn: () => apiClient.getRunTrends(12),
  });

  const topRisks = useMemo(() => {
    return (risksQuery.data ?? [])
      .filter((risk) => {
        // Filter out vendor/venv/node_modules files
        const component = risk.component.toLowerCase();
        return !component.includes('/venv/') &&
               !component.includes('/node_modules/') &&
               !component.includes('/.venv/') &&
               !component.includes('/site-packages/');
      })
      .slice()
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);
  }, [risksQuery.data]);

  const coverageGaps = useMemo(() => {
    return (coverageQuery.data ?? [])
      .filter((record) => record.component !== "__overall__" && record.value < 0.8)
      .sort((a, b) => a.value - b.value)
      .slice(0, 4);
  }, [coverageQuery.data]);

  const recommendations = useMemo(() => {
    return (recommendationsQuery.data ?? []).slice(0, 4);
  }, [recommendationsQuery.data]);

  const runs = runsQuery.data?.runs ?? [];
  const latest = runs[0];

  const highRiskCount = useMemo(() => {
    return (risksQuery.data ?? []).filter((risk) => {
      // Filter out vendor/venv files and only count high risk scores
      const component = risk.component.toLowerCase();
      const isVendor = component.includes('/venv/') ||
                       component.includes('/node_modules/') ||
                       component.includes('/.venv/') ||
                       component.includes('/site-packages/');
      return risk.score >= 65 && !isVendor;
    }).length;
  }, [risksQuery.data]);

  const avgCoverage = useMemo(() => {
    const records = (coverageQuery.data ?? []).filter((record) => record.component !== "__overall__");
    if (!records.length) {
      return null;
    }
    const value = records.reduce((acc, record) => acc + record.value, 0) / records.length;
    return Math.round(value * 100);
  }, [coverageQuery.data]);

  const coverageTrendData = useMemo(() => {
    return (trendsQuery.data?.trend ?? []).map((point) => ({
      runId: point.run_id,
      createdAt: point.created_at,
      averageCoverage: point.average_coverage,
      highRiskCount: point.high_risk_count,
    }));
  }, [trendsQuery.data]);

  const cujCoverage = cujCoverageQuery.data ?? [];

  const handleExportPDF = () => {
    setReportDialogOpen(true);
  };

  const handleExportCSV = () => {
    exportDataAsCSV(runs, "dashboard-runs");
  };

  const handleExportJSON = () => {
    exportDataAsJSON({
      runs: runsQuery.data?.runs,
      risks: risksQuery.data,
      coverage: coverageQuery.data,
      recommendations: recommendationsQuery.data,
    }, "dashboard-data");
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header with Export Menu */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Dashboard</h1>
        <ExportMenu
          onExportPDF={handleExportPDF}
          onExportCSV={handleExportCSV}
          onExportJSON={handleExportJSON}
          disabled={runsQuery.isLoading}
        />
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {runsQuery.isLoading ? (
          <MetricSkeleton />
        ) : (
          <MetricCard
            title="Total Runs"
            value={runsQuery.data?.total ?? "-"}
            subtitle="Analysis runs processed"
            icon={<Activity size={24} />}
          />
        )}
        {runsQuery.isLoading || risksQuery.isLoading ? (
          <MetricSkeleton />
        ) : (
          <Link to="/risks">
            <MetricCard
              title="High Risks"
              value={highRiskCount}
              subtitle="Score ≥ 65 - Click to view all"
              variant="critical"
              icon={<AlertCircle size={24} />}
            />
          </Link>
        )}
        {runsQuery.isLoading || coverageQuery.isLoading ? (
          <MetricSkeleton />
        ) : (
          <MetricCard
            title="Average Coverage"
            value={avgCoverage !== null ? `${avgCoverage}%` : "-"}
            subtitle="Across mapped components"
            variant="warning"
            icon={<LineChart size={24} />}
          />
        )}
        {risksQuery.isLoading ? (
          <MetricSkeleton />
        ) : (
          <MetricCard
            title="Safe Components"
            value={`${Math.max(0, (risksQuery.data?.length ?? 0) - highRiskCount)}`}
            subtitle="Score < 65 in latest run"
            variant="success"
            icon={<ShieldCheck size={24} />}
          />
        )}
      </section>

      {(runsQuery.isError || risksQuery.isError || coverageQuery.isError || recommendationsQuery.isError) && (
        <Alert variant="error" title="Dashboard data is incomplete">
          Some sections failed to load. Refresh the page after confirming the API is running.
        </Alert>
      )}

      <section className="grid gap-4 xl:grid-cols-3">
        <ResponsiveSection
          title="Risk Distribution"
          linkLabel="Full risks"
          linkTo="/risks"
          loading={risksQuery.isLoading}
          isEmpty={!risksQuery.data?.length}
          emptyMessage="No risks captured yet. Run `qaagent analyze recommendations`."
          error={risksQuery.isError ? "Unable to load risk distribution." : undefined}
        >
          <RiskDistributionChart risks={risksQuery.data ?? []} />
        </ResponsiveSection>

        <ResponsiveSection
          title="Top Risk Factors"
          linkLabel="Investigate"
          linkTo={latest ? `/runs/${latest.run_id}` : "/runs"}
          loading={risksQuery.isLoading}
          isEmpty={!risksQuery.data?.length}
          emptyMessage="Factors populate once risks are analyzed."
          error={risksQuery.isError ? "Unable to load risk factors." : undefined}
        >
          <RiskFactorsChart risks={risksQuery.data ?? []} />
        </ResponsiveSection>

        <ResponsiveSection
          title="Risk Heatmap"
          linkLabel="View risks"
          linkTo="/risks"
          loading={risksQuery.isLoading}
          isEmpty={!risksQuery.data?.length}
          emptyMessage="Run risk analysis to view churn vs coverage segments."
          error={risksQuery.isError ? "Unable to load risk heatmap." : undefined}
        >
          <RiskHeatmap risks={risksQuery.data ?? []} />
        </ResponsiveSection>
      </section>

      <section className="grid gap-4 xl:grid-cols-[2fr,1fr]">
        <ResponsiveSection
          title="Coverage Trend"
          linkLabel="See trends"
          linkTo="/trends"
          loading={trendsQuery.isLoading}
          isEmpty={!coverageTrendData.length}
          emptyMessage="Collect multiple runs to view coverage trend."
          error={trendsQuery.isError ? "Unable to load coverage trends." : undefined}
          skeleton={<Skeleton className="h-64 w-full" />}
        >
          <CoverageTrendChart data={coverageTrendData} />
        </ResponsiveSection>

        <ResponsiveSection
          title="Critical User Journey Coverage"
          linkLabel="Configure CUJs"
          linkTo="/settings"
          loading={cujCoverageQuery.isLoading}
          isEmpty={!cujCoverage.length}
          emptyMessage="Map components to CUJs in cuj.yaml to populate this view."
          error={cujCoverageQuery.isError ? "Unable to load CUJ coverage." : undefined}
          skeleton={<Skeleton className="h-64 w-full" />}
        >
          <CujCoverageRadial data={cujCoverage} />
        </ResponsiveSection>
      </section>

      <ResponsiveSection
        title="Top Risks (Your Code Only)"
        linkLabel="View all"
        linkTo={latestRunId ? `/risks?run=${latestRunId}` : "/risks"}
        loading={risksQuery.isLoading}
        isEmpty={!topRisks.length}
        emptyMessage="No risks captured yet. Run \`qaagent analyze recommendations\`."
        error={risksQuery.isError ? "Unable to load top risks." : undefined}
        skeleton={<ListSkeleton rows={4} />}
      >
        {!risksQuery.isLoading && topRisks.length > 0 && (
          <div className="mb-4 rounded-md bg-blue-50 p-3 text-xs text-blue-800 dark:bg-blue-900/20 dark:text-blue-200">
            <p className="font-medium mb-1">Risk Factors Explained:</p>
            <ul className="space-y-0.5 ml-4 list-disc">
              <li><strong>Security:</strong> Security vulnerabilities and issues found in the code</li>
              <li><strong>Coverage Gap:</strong> Low test coverage indicating untested code paths</li>
              <li><strong>Churn:</strong> High code change frequency indicating instability</li>
            </ul>
            <p className="mt-2 text-blue-700 dark:text-blue-300">
              Vendor libraries (venv, node_modules) are filtered out to focus on your application code.
            </p>
          </div>
        )}
        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {topRisks.map((risk) => (
            <Link
              key={risk.risk_id}
              to={`/risks?run=${latestRunId}&risk=${risk.risk_id}`}
              className="block py-4 transition hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <RiskBadge band={risk.band as "P0" | "P1" | "P2" | "P3"} />
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                      {risk.component}
                    </p>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                    {risk.severity.charAt(0).toUpperCase() + risk.severity.slice(1)} severity risk
                  </p>

                  {/* Risk Factors */}
                  <div className="flex flex-wrap gap-2 text-xs">
                    {risk.factors.security > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-red-700 dark:bg-red-900/20 dark:text-red-300">
                        <AlertCircle size={12} />
                        Security: {risk.factors.security.toFixed(0)}
                      </span>
                    )}
                    {risk.factors.coverage !== undefined && risk.factors.coverage > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-2 py-0.5 text-orange-700 dark:bg-orange-900/20 dark:text-orange-300">
                        <ShieldCheck size={12} />
                        Coverage Gap: {risk.factors.coverage.toFixed(0)}
                      </span>
                    )}
                    {risk.factors.churn > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-50 px-2 py-0.5 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300">
                        <Activity size={12} />
                        Churn: {risk.factors.churn.toFixed(0)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <span className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    {risk.score.toFixed(0)}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    risk score
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </ResponsiveSection>

      <div className="grid gap-4 md:grid-cols-2">
        <ResponsiveSection
          title="Coverage Gaps"
          linkLabel="Run details"
          linkTo={latest ? `/runs/${latest.run_id}` : "/runs"}
          loading={coverageQuery.isLoading}
          isEmpty={!coverageGaps.length}
          emptyMessage="Coverage data unavailable. Upload coverage reports."
          error={coverageQuery.isError ? "Unable to load coverage data." : undefined}
          skeleton={<ListSkeleton rows={4} />}
        >
          <ul className="space-y-3">
            {coverageGaps.map((record) => (
              <li key={record.coverage_id} className="rounded-md border border-slate-200 p-3 text-sm dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-800 dark:text-slate-200">{record.component}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{Math.round(record.value * 100)}%</span>
            </div>
            <div className="mt-2">
              <CoverageBar value={record.value} />
            </div>
          </li>
        ))}
      </ul>
      </ResponsiveSection>

        <ResponsiveSection
          title="Recommendations"
          linkLabel="View all"
          linkTo={latest ? `/runs/${latest.run_id}` : "/runs"}
          loading={recommendationsQuery.isLoading}
          isEmpty={!recommendations.length}
          emptyMessage="No recommendations generated yet."
          error={recommendationsQuery.isError ? "Unable to load recommendations." : undefined}
          skeleton={<ListSkeleton rows={4} />}
        >
          <ul className="space-y-3">
            {recommendations.map((rec) => (
              <li key={rec.recommendation_id} className="rounded-md border border-slate-200 p-3 text-sm dark:border-slate-700">
                <p className="font-medium text-slate-800 dark:text-slate-200">{rec.summary}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{rec.details}</p>
              </li>
            ))}
          </ul>
        </ResponsiveSection>
      </div>

      <ResponsiveSection
        title="Recent Runs"
        linkLabel="View all"
        linkTo="/runs"
        loading={runsQuery.isLoading}
        isEmpty={!runs.length}
        emptyMessage="No runs yet. Run \`qaagent analyze collectors\`."
        error={runsQuery.isError ? "Unable to load recent runs." : undefined}
        skeleton={<ListSkeleton rows={5} />}
      >
        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {runs.map((run) => (
            <Link
              key={run.run_id}
              to={`/runs/${run.run_id}`}
              className="flex items-center justify-between py-3 text-sm transition hover:text-slate-900 dark:hover:text-slate-100"
            >
              <span className="font-medium text-slate-700 dark:text-slate-200">{run.run_id}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{new Date(run.created_at).toLocaleString()}</span>
            </Link>
          ))}
        </div>
      </ResponsiveSection>
    </div>
  );
}

interface ResponsiveSectionProps {
  title: string;
  linkLabel?: string;
  linkTo?: string;
  loading: boolean;
  isEmpty: boolean;
  emptyMessage: string;
  children: ReactNode;
  error?: string;
  skeleton?: ReactNode;
}

function ResponsiveSection({
  title,
  linkLabel,
  linkTo,
  loading,
  isEmpty,
  emptyMessage,
  children,
  error,
  skeleton,
}: ResponsiveSectionProps) {
  return (
    <section className="space-y-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{title}</h2>
        {linkLabel && linkTo ? (
          <Link
            to={linkTo}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            {linkLabel}
          </Link>
        ) : null}
      </header>
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        {error ? (
          <Alert variant="error">{error}</Alert>
        ) : loading ? (
          skeleton ?? <Skeleton className="h-24 w-full" />
        ) : isEmpty ? (
          <div className="text-sm text-slate-500 dark:text-slate-400">{emptyMessage}</div>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function MetricSkeleton() {
  return (
    <div className="rounded-xl border-2 border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="mt-3 h-8 w-20" />
      <Skeleton className="mt-2 h-3 w-24" />
    </div>
  );
}

function ListSkeleton({ rows }: { rows: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  );
}
