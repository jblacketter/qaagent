import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { apiClient } from "../services/api";
import { Skeleton } from "../components/ui/Skeleton";
import { Alert } from "../components/ui/Alert";
import { ExportMenu } from "../components/ui/ExportMenu";
import { exportDataAsCSV, exportDataAsJSON, flattenForCSV } from "../utils/export";

export function RunsPage() {
  const [query, setQuery] = useState("");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["runs", { limit: 100 }],
    queryFn: () => apiClient.getRuns(100, 0),
  });

  const filteredRuns = useMemo(() => {
    const runs = data?.runs ?? [];
    if (!query.trim()) {
      return runs;
    }
    const lower = query.trim().toLowerCase();
    return runs.filter((run) => run.run_id.toLowerCase().includes(lower) || run.target.name.toLowerCase().includes(lower));
  }, [data?.runs, query]);

  const handleExportCSV = () => {
    const flattened = flattenForCSV(filteredRuns);
    exportDataAsCSV(flattened, "qa-agent-runs");
  };

  const handleExportJSON = () => {
    exportDataAsJSON(filteredRuns, "qa-agent-runs");
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-32 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return <Alert variant="error">Failed to load runs. Ensure the API is running and try again.</Alert>;
  }

  if (!data.runs.length) {
    return (
      <Alert variant="info">
        No runs available. Run <code className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">qaagent analyze collectors</code> then
        <code className="ml-1 rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">qaagent analyze risks</code> to populate this view.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Analysis Runs</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Showing {filteredRuns.length} of {data.total}</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by run ID or target"
            className="w-full max-w-xs rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
          <ExportMenu
            onExportCSV={handleExportCSV}
            onExportJSON={handleExportJSON}
            disabled={isLoading}
          />
        </div>
      </div>
      <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filteredRuns.map((run) => (
          <li
            key={run.run_id}
            className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{run.run_id}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{new Date(run.created_at).toLocaleString()}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{run.target.name}</p>
            </div>
            <Link
              to={`/runs/${run.run_id}`}
            className="mt-3 inline-flex items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            View details
          </Link>
        </li>
      ))}
      </ul>
    </div>
  );
}
