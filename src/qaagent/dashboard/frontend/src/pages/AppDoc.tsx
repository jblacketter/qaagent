import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams, Link } from "react-router-dom";
import Markdown from "react-markdown";
import { apiClient } from "../services/api";
import { FeatureCard } from "../components/Doc/FeatureCard";
import { IntegrationCard } from "../components/Doc/IntegrationCard";
import { CujCard } from "../components/Doc/CujCard";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import type { UserJourney } from "../types";

export function AppDocPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get("repo") ?? undefined;

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

  const doc = docQuery.data;
  const isLoading = docQuery.isLoading;
  const hasError = docQuery.isError;

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
                <div className="space-y-3 text-sm text-slate-600 dark:text-slate-300">
                  {doc.app_overview.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  {doc.summary}
                </p>
              )}
            </section>
          )}

          {/* AI-Enhanced Documentation */}
          {doc.agent_analysis && (
            <section className="rounded-lg border border-indigo-200 bg-indigo-50/50 p-6 dark:border-indigo-800 dark:bg-indigo-950/30">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  AI-Enhanced Documentation
                </h2>
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {doc.agent_analysis.model_used && `${doc.agent_analysis.model_used} | `}
                  {doc.agent_analysis.generated_at &&
                    new Date(doc.agent_analysis.generated_at).toLocaleString()}
                </span>
              </div>
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <Markdown>{doc.agent_analysis.enhanced_markdown}</Markdown>
              </div>
            </section>
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
        </>
      )}
    </div>
  );
}


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
