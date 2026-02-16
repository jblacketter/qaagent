import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../services/api";

interface StalenessBarProps {
  generatedAt: string;
}

function getFreshness(generatedAt: string): { label: string; color: string; bgColor: string } {
  const generated = new Date(generatedAt);
  const now = new Date();
  const hoursAgo = (now.getTime() - generated.getTime()) / (1000 * 60 * 60);

  if (hoursAgo < 24) {
    return {
      label: "Fresh",
      color: "text-green-700 dark:text-green-300",
      bgColor: "bg-green-100 dark:bg-green-900/30",
    };
  }
  if (hoursAgo < 168) {
    // 7 days
    return {
      label: "Aging",
      color: "text-yellow-700 dark:text-yellow-300",
      bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
    };
  }
  return {
    label: "Stale",
    color: "text-red-700 dark:text-red-300",
    bgColor: "bg-red-100 dark:bg-red-900/30",
  };
}

export function StalenessBar({ generatedAt }: StalenessBarProps) {
  const queryClient = useQueryClient();
  const { label, color, bgColor } = getFreshness(generatedAt);

  const regenerateMutation = useMutation({
    mutationFn: () => apiClient.regenerateDoc(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appDoc"] });
    },
  });

  const generated = new Date(generatedAt);

  return (
    <div className={`flex items-center justify-between rounded-lg ${bgColor} px-4 py-2`}>
      <div className="flex items-center gap-3">
        <span className={`text-sm font-medium ${color}`}>{label}</span>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Last generated: {generated.toLocaleString()}
        </span>
      </div>
      {label !== "Fresh" && (
        <button
          onClick={() => regenerateMutation.mutate()}
          disabled={regenerateMutation.isPending}
          className="rounded-md bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          {regenerateMutation.isPending ? "Regenerating..." : "Regenerate"}
        </button>
      )}
    </div>
  );
}
