import { useParams, useSearchParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../services/api";
import { RouteTable } from "../components/Doc/RouteTable";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";

export function FeatureDetailPage() {
  const { featureId } = useParams<{ featureId: string }>();
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get("repo") ?? undefined;
  const repoQuery = repoId ? `?repo=${encodeURIComponent(repoId)}` : "";

  const featureQuery = useQuery({
    queryKey: ["feature", featureId, repoId],
    queryFn: () => apiClient.getFeature(featureId!, repoId),
    enabled: Boolean(featureId) && Boolean(repoId),
  });

  const integrationsQuery = useQuery({
    queryKey: ["integrations", repoId],
    queryFn: () => apiClient.getIntegrations(repoId),
    enabled: Boolean(repoId),
  });

  const feature = featureQuery.data;
  const isLoading = featureQuery.isLoading;

  const connectedIntegrations = (integrationsQuery.data ?? []).filter(
    (i) => feature?.integration_ids.includes(i.id) || i.connected_features.includes(feature?.id ?? "")
  );

  if (!repoId) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Feature Detail</h1>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Select a repository to view feature details.
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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <Link to={`/doc${repoQuery}`} className="hover:text-slate-700 dark:hover:text-slate-200">
          App Docs
        </Link>
        <span>/</span>
        <span className="text-slate-900 dark:text-slate-100">{feature?.name ?? "Feature"}</span>
      </div>

      {featureQuery.isError && (
        <Alert variant="error">Feature not found.</Alert>
      )}

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {feature && (
        <>
          <section>
            <div className="flex items-start justify-between">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {feature.name}
              </h1>
              <div className="flex gap-2">
                {feature.auth_required && (
                  <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                    Auth Required
                  </span>
                )}
                {feature.crud_operations.map((op) => (
                  <span
                    key={op}
                    className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {op.toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
            {feature.description && (
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                {feature.description}
              </p>
            )}
          </section>

          {/* Routes */}
          <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
              Routes ({feature.routes.length})
            </h2>
            <RouteTable routes={feature.routes} />
          </section>

          {/* Connected Integrations */}
          {connectedIntegrations.length > 0 && (
            <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Connected Integrations
              </h2>
              <div className="space-y-3">
                {connectedIntegrations.map((integration) => (
                  <div
                    key={integration.id}
                    className="flex items-center justify-between rounded-md border border-slate-100 p-3 dark:border-slate-800"
                  >
                    <div>
                      <span className="font-medium text-slate-900 dark:text-slate-100">
                        {integration.name}
                      </span>
                      <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                        {integration.type.replace("_", " ")}
                      </span>
                    </div>
                    {integration.env_vars.length > 0 && (
                      <div className="flex gap-1">
                        {integration.env_vars.slice(0, 2).map((v) => (
                          <code
                            key={v}
                            className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                          >
                            {v}
                          </code>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Tags */}
          {feature.tags.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-medium text-slate-500 dark:text-slate-400">Tags</h2>
              <div className="flex flex-wrap gap-1">
                {feature.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
