import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import { CheckCircle2, XCircle, SkipForward, Clock, ChevronDown, ChevronRight } from "lucide-react";
import { apiClient } from "../../services/api";
import type { BranchChecklist, BranchChecklistItem } from "../../types";

const STATUS_ICONS: Record<string, typeof CheckCircle2> = {
  passed: CheckCircle2,
  failed: XCircle,
  skipped: SkipForward,
  pending: Clock,
};

const STATUS_COLORS: Record<string, string> = {
  passed: "text-emerald-600 dark:text-emerald-400",
  failed: "text-red-600 dark:text-red-400",
  skipped: "text-slate-400 dark:text-slate-500",
  pending: "text-amber-500 dark:text-amber-400",
};

const PRIORITY_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  low: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

const CATEGORY_LABELS: Record<string, string> = {
  route_change: "Route Changes",
  data_integrity: "Data Integrity",
  config: "Configuration",
  regression: "Regression",
  new_code: "New Code",
  edge_case: "Edge Cases",
};

interface ChecklistViewProps {
  checklist: BranchChecklist;
  branchId: number;
}

export function ChecklistView({ checklist, branchId }: ChecklistViewProps) {
  const queryClient = useQueryClient();
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const updateItem = useMutation({
    mutationFn: ({ itemId, status }: { itemId: number; status: string }) =>
      apiClient.updateChecklistItem(itemId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["checklist", branchId] });
    },
  });

  // Group items by category
  const groups = new Map<string, BranchChecklistItem[]>();
  for (const item of checklist.items) {
    const cat = item.category || "other";
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(item);
  }

  const toggleGroup = (cat: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const cycleStatus = (item: BranchChecklistItem) => {
    const order = ["pending", "passed", "failed", "skipped"];
    const idx = order.indexOf(item.status);
    const next = order[(idx + 1) % order.length];
    updateItem.mutate({ itemId: item.id, status: next });
  };

  // Summary stats
  const total = checklist.items.length;
  const passed = checklist.items.filter((i) => i.status === "passed").length;
  const failed = checklist.items.filter((i) => i.status === "failed").length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-400">
        <span>{passed}/{total} passed</span>
        {failed > 0 && <span className="text-red-600 dark:text-red-400">{failed} failed</span>}
        <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">
          Generated {new Date(checklist.generated_at).toLocaleDateString()}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${total > 0 ? (passed / total) * 100 : 0}%` }}
        />
      </div>

      {/* Grouped items */}
      {Array.from(groups.entries()).map(([category, items]) => {
        const collapsed = collapsedGroups.has(category);
        const Chevron = collapsed ? ChevronRight : ChevronDown;
        return (
          <div key={category} className="rounded-md border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => toggleGroup(category)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Chevron className="h-4 w-4" />
              {CATEGORY_LABELS[category] || category}
              <span className="ml-auto text-xs text-slate-400">
                {items.filter((i) => i.status === "passed").length}/{items.length}
              </span>
            </button>
            {!collapsed && (
              <ul className="divide-y divide-slate-100 border-t border-slate-200 dark:divide-slate-800 dark:border-slate-700">
                {items.map((item) => {
                  const Icon = STATUS_ICONS[item.status] || Clock;
                  return (
                    <li key={item.id} className="flex items-start gap-3 px-3 py-2">
                      <button
                        onClick={() => cycleStatus(item)}
                        className={clsx("mt-0.5 shrink-0", STATUS_COLORS[item.status])}
                        title={`Status: ${item.status} (click to cycle)`}
                      >
                        <Icon className="h-4 w-4" />
                      </button>
                      <div className="min-w-0 flex-1">
                        <p className={clsx(
                          "text-sm",
                          item.status === "passed" && "text-slate-400 line-through dark:text-slate-500",
                          item.status !== "passed" && "text-slate-700 dark:text-slate-300",
                        )}>
                          {item.description}
                        </p>
                      </div>
                      <span className={clsx("shrink-0 rounded px-1.5 py-0.5 text-xs font-medium", PRIORITY_BADGE[item.priority])}>
                        {item.priority}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
