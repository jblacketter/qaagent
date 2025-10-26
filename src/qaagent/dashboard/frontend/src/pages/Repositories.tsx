import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { FolderOpen, Plus, RefreshCw, Trash2, Eye, Clock, Loader2 } from "lucide-react";
import { apiClient } from "../services/api";
import type { Repository } from "../types";

export function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rescanning, setRescanning] = useState<Set<string>>(new Set());

  // Load repositories on mount
  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getRepositories();
      setRepositories(response.repositories);
    } catch (err) {
      console.error("Failed to load repositories:", err);
      setError(err instanceof Error ? err.message : "Failed to load repositories");
    } finally {
      setLoading(false);
    }
  };

  const handleRescan = async (repoId: string) => {
    try {
      setRescanning(prev => new Set(prev).add(repoId));

      // Update status to analyzing
      setRepositories(prev =>
        prev.map(repo =>
          repo.id === repoId ? { ...repo, status: "analyzing" as const } : repo
        )
      );

      // Trigger analysis
      await apiClient.analyzeRepository(repoId, true);

      // Reload repositories to get updated status
      await loadRepositories();
    } catch (err) {
      console.error("Failed to rescan repository:", err);
      alert(err instanceof Error ? err.message : "Failed to start analysis");

      // Reload to restore correct status
      await loadRepositories();
    } finally {
      setRescanning(prev => {
        const next = new Set(prev);
        next.delete(repoId);
        return next;
      });
    }
  };

  const handleDelete = async (repoId: string, repoName: string) => {
    if (!confirm(`Are you sure you want to delete "${repoName}"? This will remove all analysis history.`)) {
      return;
    }

    try {
      await apiClient.deleteRepository(repoId);

      // Remove from local state
      setRepositories(prev => prev.filter(repo => repo.id !== repoId));
    } catch (err) {
      console.error("Failed to delete repository:", err);
      alert(err instanceof Error ? err.message : "Failed to delete repository");
    }
  };

  const formatLastScan = (dateString: string | null) => {
    if (!dateString) return "Never";

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins} minute${diffMins !== 1 ? "s" : ""} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
    } else {
      return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ready":
        return (
          <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Ready
          </span>
        );
      case "analyzing":
        return (
          <span className="flex items-center gap-1.5 rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300">
            <Loader2 size={12} className="animate-spin" />
            Analyzing
          </span>
        );
      case "error":
        return (
          <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
            Error
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl px-4 py-12">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              My Repositories
            </h1>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              Manage and analyze your code repositories
            </p>
          </div>
          <Link
            to="/setup"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            <Plus size={18} />
            Add Repository
          </Link>
        </div>

        {/* Error State */}
        {error && (
          <div className="mt-8 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-200">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="mt-8 flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
          </div>
        ) : (
          /* Repository List */
          <div className="mt-8 space-y-4">
            {repositories.length === 0 ? (
              <div className="rounded-lg border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
                <FolderOpen className="mx-auto h-12 w-12 text-slate-400" />
                <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  No repositories yet
                </h3>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                  Get started by adding your first repository for analysis
                </p>
                <Link
                  to="/setup"
                  className="mt-6 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                >
                  <Plus size={18} />
                  Add Repository
                </Link>
              </div>
            ) : (
              repositories.map((repo) => (
                <div
                  key={repo.id}
                  className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <FolderOpen className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                        <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                          {repo.name}
                        </h3>
                        {getStatusBadge(repo.status)}
                      </div>
                      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                        {repo.path}
                      </p>
                      <div className="mt-3 flex items-center gap-6 text-xs text-slate-500 dark:text-slate-500">
                        <div className="flex items-center gap-1.5">
                          <Clock size={14} />
                          <span>Last scan: {formatLastScan(repo.last_scan)}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <RefreshCw size={14} />
                          <span>{repo.run_count} total scans</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Link
                        to={`/dashboard?repo=${repo.id}`}
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      >
                        <Eye size={16} />
                        View Dashboard
                      </Link>
                      <button
                        onClick={() => handleRescan(repo.id)}
                        disabled={repo.status === "analyzing" || rescanning.has(repo.id)}
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        title="Re-scan repository"
                      >
                        <RefreshCw size={16} className={rescanning.has(repo.id) ? "animate-spin" : ""} />
                        Re-scan
                      </button>
                      <button
                        onClick={() => handleDelete(repo.id, repo.name)}
                        disabled={repo.status === "analyzing"}
                        className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-900/50 dark:text-red-400 dark:hover:bg-red-900/20"
                        title="Delete repository"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
