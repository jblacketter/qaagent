import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { apiClient } from "../services/api";
import { RiskBadge } from "../components/ui/RiskBadge";
import { CoverageBar } from "../components/ui/CoverageBar";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";

export function RunDetailsPage() {
  const { runId = "" } = useParams();
  const [selectedRiskId, setSelectedRiskId] = useState<string | null>(null);

  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => apiClient.getRun(runId),
    enabled: Boolean(runId),
  });

  const risksQuery = useQuery({
    queryKey: ["run", runId, "risks"],
    queryFn: () => apiClient.getRisks(runId),
    enabled: Boolean(runId),
  });

  const coverageQuery = useQuery({
    queryKey: ["run", runId, "coverage"],
    queryFn: () => apiClient.getCoverage(runId),
    enabled: Boolean(runId),
  });

  const recommendationsQuery = useQuery({
    queryKey: ["run", runId, "recommendations"],
    queryFn: () => apiClient.getRecommendations(runId),
    enabled: Boolean(runId),
  });

  if (!runId) {
    return <Alert variant="error">Invalid run ID.</Alert>;
  }

  if (runQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-28 w-full" />
        <div className="grid gap-4 lg:grid-cols-[260px,1fr]">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (runQuery.isError || !runQuery.data) {
    return <Alert variant="error">Failed to load run details. Refresh once the API is available.</Alert>;
  }

  const run = runQuery.data;
  const risks = risksQuery.data ?? [];
  const coverageRecords = (coverageQuery.data ?? []).filter((record) => record.component !== "__overall__");
  const recommendations = recommendationsQuery.data ?? [];

  const selectedRisk = useMemo(
    () => risks.find((risk) => risk.risk_id === selectedRiskId) ?? risks[0] ?? null,
    [risks, selectedRiskId]
  );

  const matchingRecommendations = useMemo(() => {
    if (!selectedRisk) {
      return [];
    }
    return recommendations.filter((rec) => rec.component === selectedRisk.component);
  }, [recommendations, selectedRisk]);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">Run {run.run_id}</h2>
        <dl className="grid gap-4 text-xs sm:grid-cols-2 md:grid-cols-4">
          <Detail label="Created" value={new Date(run.created_at).toLocaleString()} />
          <Detail label="Target" value={run.target.name} />
          <Detail label="Findings" value={run.counts.findings ?? 0} />
          <Detail label="Risks" value={run.counts.risks ?? 0} />
        </dl>
      </section>

      <section className="grid gap-4 lg:grid-cols-[260px,1fr]">
        <aside className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Risks
          </h3>
          <div className="mt-3 space-y-2 text-sm">
            {risksQuery.isError && <Alert variant="error">Unable to load risks for this run.</Alert>}
            {risksQuery.isLoading && (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            )}
            {!risksQuery.isLoading && !risksQuery.isError && risks.length === 0 && <p>No risks recorded for this run.</p>}
            {!risksQuery.isLoading && !risksQuery.isError &&
              risks.map((risk) => (
                <button
                  key={risk.risk_id}
                  onClick={() => setSelectedRiskId(risk.risk_id)}
                  className={`w-full rounded-md border px-3 py-2 text-left transition dark:border-slate-700 ${
                    selectedRisk?.risk_id === risk.risk_id
                      ? "border-slate-900 bg-slate-100 dark:border-slate-200 dark:bg-slate-800"
                      : "border-slate-200 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-800 dark:text-slate-200">{risk.component}</span>
                    <RiskBadge band={risk.band as "P0" | "P1" | "P2" | "P3"} />
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">Score {risk.score.toFixed(1)}</div>
                </button>
              ))}
          </div>
          </aside>

        <div className="space-y-4">
          {risksQuery.isLoading && <Skeleton className="h-64 w-full" />}
          {risksQuery.isError && <Alert variant="error">Risk details are unavailable.</Alert>}
          {!risksQuery.isLoading && !risksQuery.isError && selectedRisk ? (
            <article className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <header className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <RiskBadge band={selectedRisk.band as "P0" | "P1" | "P2" | "P3"} />
                    <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">{selectedRisk.component}</h3>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{selectedRisk.title}</p>
                </div>
                <div className="flex flex-col items-end gap-1 text-xs text-slate-600 dark:text-slate-300">
                  <span>Score {selectedRisk.score.toFixed(1)}</span>
                  <SeverityBadge severity={selectedRisk.severity} />
                </div>
              </header>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{selectedRisk.description}</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(selectedRisk.factors).map(([name, value]) => {
                  const numericValue = typeof value === "number" ? value : Number(value ?? 0);
                  return (
                    <div key={name} className="rounded-md border border-slate-100 p-3 text-xs dark:border-slate-700">
                      <div className="uppercase tracking-wide text-slate-500 dark:text-slate-400">{name}</div>
                      <div className="text-slate-800 dark:text-slate-200">{numericValue.toFixed(1)}</div>
                    </div>
                  );
                })}
              </div>
              {recommendationsQuery.isError ? (
                <Alert variant="error">Unable to load recommendations for this component.</Alert>
              ) : recommendationsQuery.isLoading ? (
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">Loading recommendations…</p>
              ) : matchingRecommendations.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {matchingRecommendations.map((rec) => (
                    <div
                      key={rec.recommendation_id}
                      className="rounded-md border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    >
                      <p className="font-medium text-slate-700 dark:text-slate-200">{rec.summary}</p>
                      <p>{rec.details}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          ) : null}
          {!risksQuery.isLoading && !risksQuery.isError && !selectedRisk && (
            <p className="text-sm">Select a risk to view details.</p>
          )}

          <article className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <header className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-semibold">Coverage Records</h4>
              <span className="text-xs text-slate-500 dark:text-slate-400">{coverageRecords.length} entries</span>
            </header>
            {coverageQuery.isError ? (
              <Alert variant="error">Unable to load coverage details.</Alert>
            ) : (
              <div className="flex flex-col gap-2 text-xs">
                {coverageQuery.isLoading && (
                  <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, index) => (
                      <Skeleton key={index} className="h-16 w-full" />
                    ))}
                  </div>
                )}
                {!coverageQuery.isLoading && coverageRecords.length === 0 && <p>No coverage data available.</p>}
                {!coverageQuery.isLoading &&
                  coverageRecords.map((record) => (
                    <div key={record.coverage_id} className="rounded-md border border-slate-100 px-3 py-2 dark:border-slate-700">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-600 dark:text-slate-300">{record.component}</span>
                        <span className="text-slate-500 dark:text-slate-400">{Math.round(record.value * 100)}%</span>
                      </div>
                      <div className="mt-2">
                        <CoverageBar value={record.value} />
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </article>

          <article className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <header className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-semibold">Recommendations</h4>
              <span className="text-xs text-slate-500 dark:text-slate-400">{recommendations.length} items</span>
            </header>
            {recommendationsQuery.isError ? (
              <Alert variant="error">Unable to load recommendations for this run.</Alert>
            ) : (
              <div className="space-y-2 text-xs">
                {recommendationsQuery.isLoading && (
                  <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, index) => (
                      <Skeleton key={index} className="h-14 w-full" />
                    ))}
                  </div>
                )}
                {!recommendationsQuery.isLoading && recommendations.length === 0 && (
                  <p>No recommendations generated for this run.</p>
                )}
                {!recommendationsQuery.isLoading &&
                  recommendations.map((rec) => (
                    <div key={rec.recommendation_id} className="rounded-md border border-slate-100 px-3 py-2 dark:border-slate-700">
                      <p className="font-medium text-slate-700 dark:text-slate-200">{rec.summary}</p>
                      <p className="text-slate-500 dark:text-slate-400">{rec.details}</p>
                    </div>
                  ))}
              </div>
            )}
          </article>
        </div>
      </section>
    </div>
  );
}

interface DetailProps {
  label: string;
  value: string | number;
}

function Detail({ label, value }: DetailProps) {
  return (
    <div>
      <dt className="text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-slate-700 dark:text-slate-200">{value}</dd>
    </div>
  );
}
