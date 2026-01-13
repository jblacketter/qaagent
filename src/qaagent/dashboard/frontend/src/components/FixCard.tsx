import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Wrench, CheckCircle, AlertTriangle, Loader2, ExternalLink } from "lucide-react";
import { apiClient } from "../services/api";
import type { FixableCategory, ApplyFixRequest } from "../types";

interface FixCardProps {
  runId: string;
}

export function FixCard({ runId }: FixCardProps) {
  const queryClient = useQueryClient();
  const [fixingCategory, setFixingCategory] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState<{ category: string; tool: string } | null>(null);

  const fixableIssuesQuery = useQuery({
    queryKey: ["fixable-issues", runId],
    queryFn: () => apiClient.getFixableIssues(runId),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const applyFixMutation = useMutation({
    mutationFn: (request: ApplyFixRequest & { runId: string }) =>
      apiClient.applyFix(request.runId, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["fixable-issues", runId] });
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      setFixingCategory(null);
      setShowConfirm(null);
    },
    onError: () => {
      setFixingCategory(null);
      setShowConfirm(null);
    },
  });

  const handleFixClick = (category: string, tool: string) => {
    setShowConfirm({ category, tool });
  };

  const handleConfirmFix = () => {
    if (!showConfirm) return;
    setFixingCategory(showConfirm.category);
    applyFixMutation.mutate({
      runId,
      category: showConfirm.category,
      tool: showConfirm.tool,
    });
    setShowConfirm(null);
  };

  if (fixableIssuesQuery.isLoading) {
    return null;
  }

  if (fixableIssuesQuery.isError || !fixableIssuesQuery.data) {
    return null;
  }

  const { categories, total_fixable_files, total_fixable_issues, total_manual_files } = fixableIssuesQuery.data;

  if (categories.length === 0) {
    return null;
  }

  const autoFixableCategories = categories.filter((cat) => cat.auto_fixable);
  const manualCategories = categories.filter((cat) => !cat.auto_fixable);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Wrench className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Auto-Fix Available
            </h3>
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {total_fixable_issues} fixable issues across {total_fixable_files} files
          </p>
        </div>
      </div>

      {/* Auto-fixable categories */}
      {autoFixableCategories.length > 0 && (
        <div className="mt-4 space-y-3">
          {autoFixableCategories.map((category) => (
            <CategoryRow
              key={category.category}
              category={category}
              onFix={() => handleFixClick(category.category, category.tool)}
              isFixing={fixingCategory === category.category}
              disabled={fixingCategory !== null}
            />
          ))}
        </div>
      )}

      {/* Manual categories */}
      {manualCategories.length > 0 && (
        <div className="mt-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Requires Manual Review
          </p>
          {manualCategories.map((category) => (
            <CategoryRow
              key={category.category}
              category={category}
              onFix={null}
              isFixing={false}
              disabled={false}
            />
          ))}
        </div>
      )}

      {/* Fix all button */}
      {autoFixableCategories.length > 1 && (
        <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
          <button
            onClick={() => handleFixClick("all", "all")}
            disabled={fixingCategory !== null}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            {fixingCategory === "all" ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Fixing All...
              </span>
            ) : (
              `Fix All (${total_fixable_issues} issues)`
            )}
          </button>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <ConfirmationModal
          category={showConfirm.category}
          onConfirm={handleConfirmFix}
          onCancel={() => setShowConfirm(null)}
        />
      )}

      {/* Success/Error Messages */}
      {applyFixMutation.isSuccess && (
        <div className="mt-4 flex items-start gap-2 rounded-lg bg-green-50 p-3 dark:bg-green-900/20">
          <CheckCircle className="h-5 w-5 flex-shrink-0 text-green-600 dark:text-green-400" />
          <div className="flex-1 text-sm">
            <p className="font-medium text-green-900 dark:text-green-100">
              {applyFixMutation.data.message}
            </p>
            <p className="mt-1 text-green-700 dark:text-green-300">
              {applyFixMutation.data.files_modified} files modified
            </p>
          </div>
        </div>
      )}

      {applyFixMutation.isError && (
        <div className="mt-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
          <AlertTriangle className="h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400" />
          <div className="flex-1 text-sm">
            <p className="font-medium text-red-900 dark:text-red-100">
              Failed to apply fixes
            </p>
            <p className="mt-1 text-red-700 dark:text-red-300">
              {applyFixMutation.error instanceof Error ? applyFixMutation.error.message : "Unknown error"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

interface CategoryRowProps {
  category: FixableCategory;
  onFix: (() => void) | null;
  isFixing: boolean;
  disabled: boolean;
}

function CategoryRow({ category, onFix, isFixing, disabled }: CategoryRowProps) {
  const severityColors = {
    critical: "text-red-600 dark:text-red-400",
    high: "text-orange-600 dark:text-orange-400",
    medium: "text-yellow-600 dark:text-yellow-400",
    low: "text-blue-600 dark:text-blue-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    error: "text-red-600 dark:text-red-400",
  };

  const topSeverity = Object.entries(category.severity_breakdown)
    .filter(([_, count]) => count > 0)
    .sort((a, b) => {
      const order = ["critical", "error", "high", "warning", "medium", "low"];
      return order.indexOf(a[0]) - order.indexOf(b[0]);
    })[0];

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium capitalize text-slate-900 dark:text-slate-100">
            {category.category}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            ({category.tool})
          </span>
          {topSeverity && (
            <span className={`text-xs font-medium ${severityColors[topSeverity[0] as keyof typeof severityColors]}`}>
              {topSeverity[1]} {topSeverity[0]}
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
          {category.description}
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
          {category.issue_count} issues in {category.file_count} files
        </p>
      </div>
      {onFix && (
        <button
          onClick={onFix}
          disabled={disabled}
          className="ml-4 flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          {isFixing ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              Fixing...
            </>
          ) : (
            "Auto-Fix"
          )}
        </button>
      )}
      {!onFix && (
        <span className="ml-4 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
          <ExternalLink className="h-3 w-3" />
          Manual review
        </span>
      )}
    </div>
  );
}

interface ConfirmationModalProps {
  category: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmationModal({ category, onConfirm, onCancel }: ConfirmationModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Confirm Auto-Fix
        </h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {category === "all"
            ? "This will automatically fix all auto-fixable issues in your repository. Files will be modified in place."
            : `This will automatically fix ${category} issues in your repository. Files will be modified in place.`}
        </p>
        <p className="mt-2 text-sm font-medium text-amber-700 dark:text-amber-400">
          Make sure you have committed any pending changes before proceeding.
        </p>
        <div className="mt-6 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            Apply Fixes
          </button>
        </div>
      </div>
    </div>
  );
}
