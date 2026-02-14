import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../services/api";
import { IntegrationCard } from "../components/Doc/IntegrationCard";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";

const ALL_TYPES = "all";

export function IntegrationsPage() {
  const [filterType, setFilterType] = useState(ALL_TYPES);

  const integrationsQuery = useQuery({
    queryKey: ["integrations"],
    queryFn: () => apiClient.getIntegrations(),
  });

  const integrations = integrationsQuery.data ?? [];

  const types = useMemo(() => {
    const unique = new Set(integrations.map((i) => i.type));
    return [ALL_TYPES, ...Array.from(unique).sort()];
  }, [integrations]);

  const filtered = useMemo(() => {
    if (filterType === ALL_TYPES) return integrations;
    return integrations.filter((i) => i.type === filterType);
  }, [integrations, filterType]);

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          External Integrations
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          External services and dependencies detected in the codebase.
        </p>
      </section>

      {integrationsQuery.isError && (
        <Alert variant="error">
          Failed to load integrations. Run <code>qaagent doc generate</code> first.
        </Alert>
      )}

      {integrationsQuery.isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )}

      {!integrationsQuery.isLoading && integrations.length > 0 && (
        <>
          {/* Type filter */}
          <div className="flex flex-wrap gap-2">
            {types.map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  filterType === type
                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                {type === ALL_TYPES ? "All" : type.replace("_", " ")}
              </button>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filtered.map((integration) => (
              <IntegrationCard key={integration.id} integration={integration} />
            ))}
          </div>
        </>
      )}

      {!integrationsQuery.isLoading && integrations.length === 0 && !integrationsQuery.isError && (
        <section className="rounded-lg border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
          <p className="text-slate-500 dark:text-slate-400">
            No integrations detected. Run{" "}
            <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">qaagent doc generate</code>
            {" "}to analyze your codebase.
          </p>
        </section>
      )}
    </div>
  );
}
