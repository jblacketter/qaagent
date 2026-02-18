import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import Markdown from "react-markdown";
import { apiClient } from "../services/api";
import { FeatureCard } from "../components/Doc/FeatureCard";
import { IntegrationCard } from "../components/Doc/IntegrationCard";
import { CujCard } from "../components/Doc/CujCard";
import { StalenessBar } from "../components/Doc/StalenessBar";
import { FeatureMapDiagram } from "../components/Doc/FeatureMapDiagram";
import { IntegrationMapDiagram } from "../components/Doc/IntegrationMapDiagram";
import { RouteGraphDiagram } from "../components/Doc/RouteGraphDiagram";
import { RouteTable } from "../components/Doc/RouteTable";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import { useAutoRepo } from "../hooks/useAutoRepo";
import type { UserJourney, RouteDoc } from "../types";

export function AppDocPage() {
  const queryClient = useQueryClient();
  const { repoId, isRedirecting } = useAutoRepo();

  const docQuery = useQuery({
    queryKey: ["appDoc", repoId],
    queryFn: () => apiClient.getAppDoc(repoId),
    enabled: Boolean(repoId),
  });

  const regenerateMutation = useMutation({
    mutationFn: () => apiClient.regenerateDoc(true, repoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appDoc", repoId] });
    },
  });

  const handleExportMarkdown = async () => {
    try {
      const md = await apiClient.exportDocMarkdown(repoId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "app-documentation.md";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently fail
    }
  };

  // Auto-selecting single repo
  if (isRedirecting) {
    return (
      <div className="flex items-center justify-center py-20">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }

  // No repo selected — prompt user
  if (!repoId) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          App Documentation
        </h1>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Select a repository to view its documentation.
        </p>
        <Link
          to="/repositories"
          className="mt-6 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          Go to Repositories
        </Link>
      </div>
    );
  }

  const [archTab, setArchTab] = useState<"feature" | "integration" | "route">("feature");
  const [routesExpanded, setRoutesExpanded] = useState(false);

  const doc = docQuery.data;
  const isLoading = docQuery.isLoading;
  const hasError = docQuery.isError;

  // Aggregate all routes from features for the route table
  const allRoutes: RouteDoc[] = useMemo(() => {
    if (!doc) return [];
    return doc.features.flatMap((f) => f.routes);
  }, [doc]);

  // Filter architecture nodes/edges per diagram type
  const archData = useMemo(() => {
    if (!doc) return { feature: { nodes: [], edges: [] }, integration: { nodes: [], edges: [] }, route: { nodes: [], edges: [] } };
    const nodes = doc.architecture_nodes ?? [];
    const edges = doc.architecture_edges ?? [];

    const featureNodes = nodes.filter((n) => n.type === "feature");
    const featureIds = new Set(featureNodes.map((n) => n.id));
    const featureEdges = edges.filter((e) => featureIds.has(e.source) && featureIds.has(e.target));

    const integrationNodes = nodes.filter((n) => n.type === "feature" || n.type === "integration");
    const integrationIds = new Set(integrationNodes.map((n) => n.id));
    const integrationEdges = edges.filter((e) => integrationIds.has(e.source) && integrationIds.has(e.target));

    const routeNodes = nodes.filter((n) => n.type === "route_group");
    const routeIds = new Set(routeNodes.map((n) => n.id));
    const routeEdges = edges.filter((e) => routeIds.has(e.source) && routeIds.has(e.target));

    return {
      feature: { nodes: featureNodes, edges: featureEdges },
      integration: { nodes: integrationNodes, edges: integrationEdges },
      route: { nodes: routeNodes, edges: routeEdges },
    };
  }, [doc]);

  const hasArchData = archData.feature.nodes.length > 0 || archData.integration.nodes.length > 0 || archData.route.nodes.length > 0;

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {doc?.app_name ?? "App"} Documentation
            </h1>
            {doc && (
              <p className="text-xs text-slate-400 dark:text-slate-500">
                {doc.total_routes} routes | {doc.features.length} features | {doc.integrations.length} integrations
                {" | "}Generated {new Date(doc.generated_at).toLocaleString()}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleExportMarkdown}
              disabled={isLoading || hasError}
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              Export MD
            </button>
            <button
              onClick={() => regenerateMutation.mutate()}
              disabled={regenerateMutation.isPending}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              {regenerateMutation.isPending ? "Regenerating..." : "Regenerate"}
            </button>
          </div>
        </div>
      </section>

      {doc && (
        <StalenessBar generatedAt={doc.generated_at} repoId={repoId} />
      )}

      {hasError && (
        <Alert variant="error">
          No documentation found. Analyze this repository first, or click Regenerate.
        </Alert>
      )}

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        </div>
      )}

      {doc && (
        <>
          {/* App Overview */}
          {(doc.app_overview || doc.summary) && (
            <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Overview
              </h2>
              {doc.app_overview ? (
                <div className="space-y-3 text-base leading-7 text-slate-600 dark:text-slate-300">
                  {doc.app_overview.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
              ) : (
                <p className="text-base leading-7 text-slate-600 dark:text-slate-300">
                  {doc.summary}
                </p>
              )}
            </section>
          )}

          {/* AI-Enhanced Documentation — section cards */}
          {doc.agent_analysis && (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  AI-Enhanced Documentation
                </h2>
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {doc.agent_analysis.model_used && `${doc.agent_analysis.model_used} | `}
                  {doc.agent_analysis.generated_at &&
                    new Date(doc.agent_analysis.generated_at).toLocaleString()}
                </span>
              </div>

              {doc.agent_analysis.sections && doc.agent_analysis.sections.length > 0 ? (
                <div className="space-y-4">
                  {doc.agent_analysis.sections.map((section, idx) => {
                    const colors = sectionColors[section.title] ?? defaultSectionColor;
                    return (
                      <section
                        key={idx}
                        className={`rounded-lg border ${colors.border} ${colors.bg} p-6`}
                      >
                        <div className="mb-3 flex items-center gap-2">
                          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                            {section.title}
                          </h3>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors.badge}`}>
                            AI
                          </span>
                        </div>
                        <div className="prose prose-base max-w-none dark:prose-invert prose-headings:font-semibold prose-headings:text-slate-900 dark:prose-headings:text-slate-100 prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2 prose-p:leading-7 prose-p:text-slate-600 dark:prose-p:text-slate-300 prose-li:text-slate-600 dark:prose-li:text-slate-300 prose-li:leading-7 prose-ul:my-3 prose-ol:my-3 prose-table:text-sm prose-th:bg-slate-100 dark:prose-th:bg-slate-800 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-strong:text-slate-800 dark:prose-strong:text-slate-200 prose-code:text-sm prose-code:bg-slate-100 dark:prose-code:bg-slate-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-blockquote:border-l-4 prose-blockquote:border-slate-300 dark:prose-blockquote:border-slate-600 prose-blockquote:bg-slate-50 dark:prose-blockquote:bg-slate-800/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-lg prose-blockquote:not-italic">
                          <Markdown>{section.content}</Markdown>
                        </div>
                      </section>
                    );
                  })}
                </div>
              ) : (
                <section className="rounded-lg border border-indigo-200 bg-indigo-50/50 p-6 dark:border-indigo-800 dark:bg-indigo-950/30">
                  <div className="prose prose-base max-w-none dark:prose-invert prose-headings:font-semibold prose-headings:text-slate-900 dark:prose-headings:text-slate-100 prose-h2:text-xl prose-h2:border-b prose-h2:border-slate-200 dark:prose-h2:border-slate-700 prose-h2:pb-2 prose-h2:mb-4 prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2 prose-p:leading-7 prose-p:text-slate-600 dark:prose-p:text-slate-300 prose-li:text-slate-600 dark:prose-li:text-slate-300 prose-li:leading-7 prose-ul:my-3 prose-ol:my-3 prose-table:text-sm prose-th:bg-slate-100 dark:prose-th:bg-slate-800 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-strong:text-slate-800 dark:prose-strong:text-slate-200 prose-code:text-sm prose-code:bg-slate-100 dark:prose-code:bg-slate-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-blockquote:border-l-4 prose-blockquote:border-slate-300 dark:prose-blockquote:border-slate-600 prose-blockquote:bg-slate-50 dark:prose-blockquote:bg-slate-800/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-lg prose-blockquote:not-italic">
                    <Markdown>{doc.agent_analysis.enhanced_markdown}</Markdown>
                  </div>
                </section>
              )}
            </>
          )}

          {/* Tech Stack */}
          {doc.tech_stack && doc.tech_stack.length > 0 && (
            <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Tech Stack
              </h2>
              <div className="flex flex-wrap gap-2">
                {doc.tech_stack.map((tech) => (
                  <span
                    key={tech}
                    className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* User Roles */}
          {doc.user_roles && doc.user_roles.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                User Roles ({doc.user_roles.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {doc.user_roles.map((role) => (
                  <div
                    key={role.id}
                    className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
                  >
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                      {role.name}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {role.description}
                    </p>
                    {role.permissions.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {role.permissions.map((perm) => (
                          <span
                            key={perm}
                            className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                          >
                            {perm}
                          </span>
                        ))}
                      </div>
                    )}
                    {role.associated_features.length > 0 && (
                      <p className="mt-2 text-xs text-slate-400">
                        {role.associated_features.length} feature area(s)
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* User Journeys */}
          {doc.user_journeys && doc.user_journeys.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                User Journeys ({doc.user_journeys.length})
              </h2>
              <div className="space-y-3">
                {doc.user_journeys.map((journey) => (
                  <JourneyCard key={journey.id} journey={journey} />
                ))}
              </div>
            </section>
          )}

          {/* Features */}
          {doc.features.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Features ({doc.features.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {doc.features.map((feature) => (
                  <FeatureCard key={feature.id} feature={feature} repoId={repoId} />
                ))}
              </div>
            </section>
          )}

          {/* Integrations */}
          {doc.integrations.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                External Integrations ({doc.integrations.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {doc.integrations.map((integration) => (
                  <IntegrationCard key={integration.id} integration={integration} />
                ))}
              </div>
            </section>
          )}

          {/* CUJs */}
          {doc.discovered_cujs.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Critical User Journeys ({doc.discovered_cujs.length})
              </h2>
              <div className="space-y-3">
                {doc.discovered_cujs.map((cuj) => (
                  <CujCard key={cuj.id} cuj={cuj} />
                ))}
              </div>
            </section>
          )}

          {/* All Routes */}
          {allRoutes.length > 0 && (
            <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <button
                onClick={() => setRoutesExpanded(!routesExpanded)}
                className="flex w-full items-center justify-between p-4 text-left"
              >
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  All Routes ({allRoutes.length})
                </h2>
                <span className="text-slate-400">{routesExpanded ? "\u25B2" : "\u25BC"}</span>
              </button>
              {routesExpanded && (
                <div className="border-t border-slate-200 p-4 dark:border-slate-800">
                  <RouteTable routes={allRoutes} />
                </div>
              )}
            </section>
          )}

          {/* Architecture Diagrams */}
          {hasArchData && (
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Architecture
              </h2>
              <div className="mb-3 flex gap-1">
                {archData.feature.nodes.length > 0 && (
                  <button
                    onClick={() => setArchTab("feature")}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                      archTab === "feature"
                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                  >
                    Feature Map
                  </button>
                )}
                {archData.integration.nodes.length > 0 && (
                  <button
                    onClick={() => setArchTab("integration")}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                      archTab === "integration"
                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                  >
                    Integration Map
                  </button>
                )}
                {archData.route.nodes.length > 0 && (
                  <button
                    onClick={() => setArchTab("route")}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                      archTab === "route"
                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                  >
                    Route Graph
                  </button>
                )}
              </div>
              {archTab === "feature" && archData.feature.nodes.length > 0 && (
                <FeatureMapDiagram nodes={archData.feature.nodes} edges={archData.feature.edges} />
              )}
              {archTab === "integration" && archData.integration.nodes.length > 0 && (
                <IntegrationMapDiagram nodes={archData.integration.nodes} edges={archData.integration.edges} />
              )}
              {archTab === "route" && archData.route.nodes.length > 0 && (
                <RouteGraphDiagram nodes={archData.route.nodes} edges={archData.route.edges} />
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}


const sectionColors: Record<string, { border: string; bg: string; badge: string }> = {
  "Product Overview": { border: "border-indigo-200 dark:border-indigo-800", bg: "bg-indigo-50/30 dark:bg-indigo-950/20", badge: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300" },
  "Architecture & Tech Stack": { border: "border-blue-200 dark:border-blue-800", bg: "bg-blue-50/30 dark:bg-blue-950/20", badge: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" },
  "Features": { border: "border-emerald-200 dark:border-emerald-800", bg: "bg-emerald-50/30 dark:bg-emerald-950/20", badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" },
  "User Roles & Permissions": { border: "border-purple-200 dark:border-purple-800", bg: "bg-purple-50/30 dark:bg-purple-950/20", badge: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300" },
  "User Journeys": { border: "border-amber-200 dark:border-amber-800", bg: "bg-amber-50/30 dark:bg-amber-950/20", badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  "Integrations": { border: "border-cyan-200 dark:border-cyan-800", bg: "bg-cyan-50/30 dark:bg-cyan-950/20", badge: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300" },
  "Configuration & Getting Started": { border: "border-teal-200 dark:border-teal-800", bg: "bg-teal-50/30 dark:bg-teal-950/20", badge: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300" },
  "Gaps & Recommendations": { border: "border-rose-200 dark:border-rose-800", bg: "bg-rose-50/30 dark:bg-rose-950/20", badge: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300" },
};
const defaultSectionColor = { border: "border-slate-200 dark:border-slate-800", bg: "bg-slate-50/30 dark:bg-slate-950/20", badge: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" };

const priorityColors = {
  high: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  medium: "bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  low: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300",
};

function JourneyCard({ journey }: { journey: UserJourney }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">
            {journey.name}
          </h3>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              priorityColors[journey.priority] ?? priorityColors.medium
            }`}
          >
            {journey.priority}
          </span>
          <span className="text-xs text-slate-400">
            {journey.steps.length} step(s) | actor: {journey.actor}
          </span>
        </div>
        <span className="text-slate-400">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>
      {expanded && (
        <div className="border-t border-slate-200 p-4 dark:border-slate-800">
          <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
            {journey.description}
          </p>
          <ol className="space-y-2">
            {journey.steps.map((step) => (
              <li key={step.order} className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {step.order}
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {step.action}
                  </p>
                  {step.page_or_route && (
                    <p className="text-xs text-slate-400">
                      <code>{step.page_or_route}</code>
                    </p>
                  )}
                  {step.expected_outcome && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Expected: {step.expected_outcome}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
