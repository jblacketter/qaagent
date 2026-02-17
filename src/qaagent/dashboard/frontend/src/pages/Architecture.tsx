import { useState, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../services/api";
import { FeatureMapDiagram } from "../components/Doc/FeatureMapDiagram";
import { IntegrationMapDiagram } from "../components/Doc/IntegrationMapDiagram";
import { RouteGraphDiagram } from "../components/Doc/RouteGraphDiagram";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";

type DiagramType = "feature_map" | "integration_map" | "route_graph";

const tabs: { key: DiagramType; label: string }[] = [
  { key: "feature_map", label: "Feature Map" },
  { key: "integration_map", label: "Integration Map" },
  { key: "route_graph", label: "Route Graph" },
];

export function ArchitecturePage() {
  const [activeTab, setActiveTab] = useState<DiagramType>("feature_map");
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get("repo") ?? undefined;

  const archQuery = useQuery({
    queryKey: ["architecture", repoId],
    queryFn: () => apiClient.getArchitecture(repoId),
    enabled: Boolean(repoId),
  });

  const filteredData = useMemo(() => {
    const allNodes = archQuery.data?.nodes ?? [];
    const allEdges = archQuery.data?.edges ?? [];

    const nodes = allNodes.filter(
      (n) => n.metadata?.graph_type === activeTab
    );
    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = allEdges.filter(
      (e) => e.type.startsWith(activeTab + ":") && nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    return { nodes, edges };
  }, [archQuery.data, activeTab]);

  if (!repoId) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Architecture</h1>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Select a repository to view its architecture diagrams.
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
      <section className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Architecture
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Interactive architecture diagrams of your application.
        </p>
      </section>

      {archQuery.isError && (
        <Alert variant="error">
          Failed to load architecture data. Run <code>qaagent doc generate</code> first.
        </Alert>
      )}

      {/* Tab selector */}
      <div className="flex gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key
                ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {archQuery.isLoading && <Skeleton className="h-[500px] w-full" />}

      {!archQuery.isLoading && !archQuery.isError && (
        <>
          {filteredData.nodes.length === 0 ? (
            <section className="rounded-lg border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
              <p className="text-slate-500 dark:text-slate-400">
                No data for this diagram type. Generate documentation with{" "}
                <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">qaagent doc generate</code>.
              </p>
            </section>
          ) : (
            <>
              {activeTab === "feature_map" && (
                <FeatureMapDiagram nodes={filteredData.nodes} edges={filteredData.edges} />
              )}
              {activeTab === "integration_map" && (
                <IntegrationMapDiagram nodes={filteredData.nodes} edges={filteredData.edges} />
              )}
              {activeTab === "route_graph" && (
                <RouteGraphDiagram nodes={filteredData.nodes} edges={filteredData.edges} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
