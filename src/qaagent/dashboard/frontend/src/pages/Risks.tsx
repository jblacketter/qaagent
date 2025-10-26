import { useMemo, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from "lucide-react";

import { apiClient } from "../services/api";
import { RiskBadge } from "../components/ui/RiskBadge";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import { ExportMenu } from "../components/ui/ExportMenu";
import { exportDataAsCSV, exportDataAsJSON, flattenForCSV } from "../utils/export";

export function RisksPage() {
  const [searchParams] = useSearchParams();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRiskId, setSelectedRiskId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());


  const runsQuery = useQuery({
    queryKey: ["runs", { limit: 30 }],
    queryFn: () => apiClient.getRuns(30, 0),
  });

  // Auto-select run and risk from URL parameters
  useEffect(() => {
    const runParam = searchParams.get('run');
    const riskParam = searchParams.get('risk');

    if (runParam && !selectedRunId) {
      setSelectedRunId(runParam);
    }

    if (riskParam && !selectedRiskId) {
      setSelectedRiskId(riskParam);
    }
  }, [searchParams, selectedRunId, selectedRiskId]);

  const risksQuery = useQuery({
    queryKey: ["riskExplorer", selectedRunId],
    queryFn: () => (selectedRunId ? apiClient.getRisks(selectedRunId) : Promise.resolve([])),
    enabled: Boolean(selectedRunId),
  });

  const recommendationsQuery = useQuery({
    queryKey: ["riskExplorer", "recommendations", selectedRunId],
    queryFn: () => (selectedRunId ? apiClient.getRecommendations(selectedRunId) : Promise.resolve([])),
    enabled: Boolean(selectedRunId),
  });

  const allRisks = risksQuery.data ?? [];

  // Filter out vendor/library files
  const risks = useMemo(() => {
    return allRisks.filter((risk) => {
      const component = risk.component.toLowerCase();
      return !component.includes('/venv/') &&
             !component.includes('/node_modules/') &&
             !component.includes('/.venv/') &&
             !component.includes('/site-packages/');
    });
  }, [allRisks]);

  // Group risks by severity with priority order
  const groupedRisks = useMemo(() => {
    const severityOrder = ['critical', 'high', 'medium', 'low'];
    const groups: Record<string, typeof risks> = {
      critical: [],
      high: [],
      medium: [],
      low: [],
    };

    risks.forEach((risk) => {
      const severity = risk.severity.toLowerCase();
      if (groups[severity]) {
        groups[severity].push(risk);
      }
    });

    // Sort each group by score (highest first)
    Object.keys(groups).forEach((severity) => {
      groups[severity].sort((a, b) => b.score - a.score);
    });

    return severityOrder.map((severity) => ({
      severity,
      risks: groups[severity],
      count: groups[severity].length,
    })).filter((group) => group.count > 0);
  }, [risks]);

  const toggleSection = (severity: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(severity)) {
        next.delete(severity);
      } else {
        next.add(severity);
      }
      return next;
    });
  };

  const selectedRisk = useMemo(
    () => risks.find((risk) => risk.risk_id === selectedRiskId) ?? risks[0] ?? null,
    [risks, selectedRiskId]
  );

  const matchingRecommendations = useMemo(() => {
    if (!selectedRisk) {
      return [];
    }
    return (recommendationsQuery.data ?? []).filter((rec) => rec.component === selectedRisk.component);
  }, [recommendationsQuery.data, selectedRisk]);

  const handleExportCSV = () => {
    const flattened = flattenForCSV(risks);
    exportDataAsCSV(flattened, `qa-agent-risks-${selectedRunId || 'all'}`);
  };

  const handleExportJSON = () => {
    exportDataAsJSON(risks, `qa-agent-risks-${selectedRunId || 'all'}`);
  };

  return (
    <div className="relative grid gap-6" style={{ gridTemplateColumns: sidebarCollapsed ? '60px 1fr' : '280px 1fr' }}>
      <aside className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 relative">
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-4 z-10 rounded-full border border-slate-300 bg-white p-1 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>

        {!sidebarCollapsed && (
          <div className="p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Runs</h2>
        <div className="mt-3 space-y-2 text-sm">
          {runsQuery.isError && <Alert variant="error">Unable to load runs. Check the API and try again.</Alert>}
          {runsQuery.isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          )}
          {!runsQuery.isLoading && !runsQuery.isError && runsQuery.data?.runs.length === 0 && (
            <Alert variant="info">No runs available yet. Generate evidence to explore risks.</Alert>
          )}
          {!runsQuery.isLoading && !runsQuery.isError &&
            runsQuery.data?.runs.map((run) => (
              <button
                key={run.run_id}
                onClick={() => {
                  setSelectedRunId(run.run_id);
                  setSelectedRiskId(null);
                }}
                className={`w-full rounded-md border px-3 py-2 text-left transition dark:border-slate-700 ${
                  selectedRunId === run.run_id
                    ? "border-slate-900 bg-slate-100 dark:border-slate-200 dark:bg-slate-800"
                    : "border-slate-200 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                }`}
              >
                <div className="font-medium text-slate-700 dark:text-slate-200">{run.run_id}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{new Date(run.created_at).toLocaleString()}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{run.target.name}</div>
              </button>
            ))}
          </div>
        </div>
        )}

        {sidebarCollapsed && (
          <div className="p-2 text-center">
            <p className="text-xs text-slate-500 dark:text-slate-400 transform -rotate-90 whitespace-nowrap mt-8">Runs</p>
          </div>
        )}
      </aside>

      <section className="space-y-4">
        <header className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Risks (Application Code Only)</h2>
            {selectedRunId && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {risks.length} items • Vendor libraries filtered
              </span>
            )}
          </div>
          {selectedRunId && risks.length > 0 && (
            <ExportMenu
              onExportCSV={handleExportCSV}
              onExportJSON={handleExportJSON}
              disabled={risksQuery.isLoading}
            />
          )}
        </header>

        {!selectedRunId && <Alert variant="info">Select a run to explore risks and contributing factors.</Alert>}
        {selectedRunId && risksQuery.isError && <Alert variant="error">Failed to load risks for this run.</Alert>}
        {selectedRunId && risksQuery.isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full" />
            ))}
          </div>
        )}
        {selectedRunId && !risksQuery.isLoading && !risksQuery.isError && risks.length === 0 && (
          <Alert variant="info">No risks were recorded for this run.</Alert>
        )}

        <div className="grid gap-4 lg:grid-cols-[320px,1fr]">
          <div className="space-y-3">
            {!risksQuery.isLoading && !risksQuery.isError &&
              groupedRisks.map((group) => (
                <div key={group.severity} className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
                  <button
                    onClick={() => toggleSection(group.severity)}
                    className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  >
                    <div className="flex items-center gap-3">
                      <SeverityBadge severity={group.severity} />
                      <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 capitalize">
                        {group.severity}
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {group.count} {group.count === 1 ? 'risk' : 'risks'}
                      </span>
                    </div>
                    {collapsedSections.has(group.severity) ? (
                      <ChevronDown size={18} className="text-slate-500 dark:text-slate-400" />
                    ) : (
                      <ChevronUp size={18} className="text-slate-500 dark:text-slate-400" />
                    )}
                  </button>

                  {!collapsedSections.has(group.severity) && (
                    <div className="border-t border-slate-200 dark:border-slate-800">
                      {group.risks.map((risk) => (
                        <button
                          key={risk.risk_id}
                          onClick={() => setSelectedRiskId(risk.risk_id)}
                          className={`w-full border-b border-slate-200 px-4 py-3 text-left text-sm transition last:border-b-0 dark:border-slate-800 ${
                            selectedRiskId === risk.risk_id
                              ? "bg-blue-50 ring-2 ring-inset ring-blue-500/20 dark:bg-blue-900/30 dark:ring-blue-400/20"
                              : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-slate-800 dark:text-slate-200 truncate pr-2">
                              {risk.component}
                            </span>
                            <RiskBadge band={risk.band as "P0" | "P1" | "P2" | "P3"} />
                          </div>
                          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                            <span className="truncate pr-2">{risk.title}</span>
                            <span className="font-semibold">{risk.score.toFixed(0)}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
          </div>

          {selectedRisk && (
            <article className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <header className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <RiskBadge band={selectedRisk.band as "P0" | "P1" | "P2" | "P3"} />
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{selectedRisk.component}</h3>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{selectedRisk.title}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">{selectedRisk.score.toFixed(0)}</span>
                  <SeverityBadge severity={selectedRisk.severity} />
                </div>
              </header>

              {/* Why is this risky section */}
              <div className="mt-4 rounded-md bg-red-50 border border-red-200 p-4 dark:bg-red-900/10 dark:border-red-900/30">
                <h4 className="text-sm font-semibold text-red-900 dark:text-red-200 mb-3">⚠ Why is this risky?</h4>

                {selectedRisk.factors.security > 0 && (
                  <div className="space-y-2 mb-3">
                    <p className="text-sm text-red-800 dark:text-red-300 font-medium">
                      This file has {selectedRisk.factors.security.toFixed(0)} security finding(s) that need immediate attention.
                    </p>
                    <div className="text-sm text-red-700 dark:text-red-400 pl-4 space-y-1">
                      <p>Possible security issues in <code className="bg-red-100 dark:bg-red-900/30 px-1 rounded">{selectedRisk.component}</code>:</p>
                      <ul className="list-disc list-inside space-y-0.5">
                        <li>Hardcoded credentials or secrets</li>
                        <li>SQL injection or command injection vulnerabilities</li>
                        <li>Insecure cryptographic algorithms</li>
                        <li>Improper input validation or sanitization</li>
                        <li>Unsafe deserialization</li>
                      </ul>
                    </div>
                  </div>
                )}

                {selectedRisk.factors.coverage !== undefined && selectedRisk.factors.coverage > 0 && (
                  <p className="text-sm text-amber-800 dark:text-amber-300 mb-2">
                    <strong>No test coverage:</strong> This code is untested, meaning bugs and regressions can easily slip through.
                  </p>
                )}

                {selectedRisk.factors.churn > 0 && (
                  <p className="text-sm text-yellow-800 dark:text-yellow-300">
                    <strong>High change frequency:</strong> This file changes often ({selectedRisk.factors.churn.toFixed(0)}), indicating instability or unclear requirements.
                  </p>
                )}
              </div>

              <h4 className="mt-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Risk Factor Breakdown</h4>
              <div className="mt-2 grid gap-3 md:grid-cols-3">
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
              {/* Recommendations Section */}
              <div className="mt-6">
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">✓ What should you do?</h4>
                {recommendationsQuery.isError ? (
                  <Alert variant="error">Unable to load recommendations for this component.</Alert>
                ) : recommendationsQuery.isLoading ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">Loading recommendations…</p>
                ) : matchingRecommendations.length > 0 ? (
                  <div className="space-y-3">
                    {matchingRecommendations.map((rec) => (
                      <div
                        key={rec.recommendation_id}
                        className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/50 dark:bg-blue-900/20"
                      >
                        <p className="font-semibold text-blue-900 dark:text-blue-200 mb-1">{rec.summary}</p>
                        <p className="text-sm text-blue-800 dark:text-blue-300">{rec.details}</p>
                        {rec.priority && (
                          <span className="inline-block mt-2 text-xs px-2 py-1 rounded-full bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-200">
                            {rec.priority} priority
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {selectedRisk.factors.security > 0 && (
                      <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/50 dark:bg-blue-900/20">
                        <p className="font-semibold text-blue-900 dark:text-blue-200 mb-2">1. Investigate Security Findings</p>
                        <p className="text-sm text-blue-800 dark:text-blue-300 mb-2">
                          Manually review <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">{selectedRisk.component}</code> for:
                        </p>
                        <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1 ml-4">
                          <li>• Hardcoded passwords, API keys, or secrets</li>
                          <li>• User input that isn't validated or escaped</li>
                          <li>• Unsafe functions like <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">eval()</code>, <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">exec()</code>, or <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">pickle.loads()</code></li>
                          <li>• SQL queries built with string concatenation</li>
                          <li>• Missing authentication or authorization checks</li>
                        </ul>
                        <p className="text-sm text-blue-800 dark:text-blue-300 mt-2">
                          <strong>Tools:</strong> Run <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">bandit</code> (Python), <code className="bg-blue-100 dark:bg-blue-900/40 px-1 rounded">semgrep</code>, or your IDE's security scanner on this file.
                        </p>
                      </div>
                    )}

                    {(selectedRisk.factors.coverage ?? 0) > 0 && (
                      <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/50 dark:bg-blue-900/20">
                        <p className="font-semibold text-blue-900 dark:text-blue-200 mb-2">
                          {selectedRisk.factors.security > 0 ? "2" : "1"}. Add Test Coverage
                        </p>
                        <p className="text-sm text-blue-800 dark:text-blue-300">
                          Write unit tests for critical functions in this file to catch regressions and verify correct behavior.
                        </p>
                      </div>
                    )}

                    {selectedRisk.factors.churn > 0 && (
                      <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/50 dark:bg-blue-900/20">
                        <p className="font-semibold text-blue-900 dark:text-blue-200 mb-2">
                          {[selectedRisk.factors.security > 0, (selectedRisk.factors.coverage ?? 0) > 0].filter(Boolean).length + 1}. Stabilize This Code
                        </p>
                        <p className="text-sm text-blue-800 dark:text-blue-300">
                          High change frequency suggests unclear requirements or design issues. Consider refactoring for better stability.
                        </p>
                      </div>
                    )}

                    <div className="rounded-md border border-slate-300 bg-slate-100 p-4 dark:border-slate-600 dark:bg-slate-800">
                      <p className="font-semibold text-slate-900 dark:text-slate-100 mb-2">
                        📋 Next Steps:
                      </p>
                      <ol className="text-sm text-slate-700 dark:text-slate-300 space-y-1 ml-4 list-decimal">
                        <li>Open the file: <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">{selectedRisk.component}</code></li>
                        <li>Check the evidence files in <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">~/.qaagent/runs/{selectedRunId}/evidence/</code></li>
                        <li>Run security scanner: <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">bandit {selectedRisk.component}</code></li>
                        <li>Fix identified issues and commit changes</li>
                        <li>Re-run analysis to verify fixes</li>
                      </ol>
                    </div>
                  </div>
                )}
              </div>
            </article>
          )}
        </div>
      </section>
    </div>
  );
}
