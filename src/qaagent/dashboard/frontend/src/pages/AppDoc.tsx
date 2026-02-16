import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../services/api";
import { FeatureCard } from "../components/Doc/FeatureCard";
import { IntegrationCard } from "../components/Doc/IntegrationCard";
import { CujCard } from "../components/Doc/CujCard";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";

export function AppDocPage() {
  const queryClient = useQueryClient();

  const docQuery = useQuery({
    queryKey: ["appDoc"],
    queryFn: () => apiClient.getAppDoc(),
  });

  const regenerateMutation = useMutation({
    mutationFn: () => apiClient.regenerateDoc(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appDoc"] });
    },
  });

  const handleExportMarkdown = async () => {
    try {
      const md = await apiClient.exportDocMarkdown();
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
          No documentation found. Run <code>qaagent doc generate</code> to create it.
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
          {/* Summary */}
          {doc.summary && (
            <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                Summary
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {doc.summary}
              </p>
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
                  <FeatureCard key={feature.id} feature={feature} />
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
