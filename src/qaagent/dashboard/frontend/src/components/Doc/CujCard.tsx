import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { DiscoveredCUJ } from "../../types";

interface CujCardProps {
  cuj: DiscoveredCUJ;
}

export function CujCard({ cuj }: CujCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {cuj.name}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {cuj.steps.length} step{cuj.steps.length !== 1 ? "s" : ""}
            {cuj.pattern && (
              <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {cuj.pattern.replace("_", " ")}
              </span>
            )}
          </p>
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3 dark:border-slate-800">
          {cuj.description && (
            <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
              {cuj.description}
            </p>
          )}
          <ol className="space-y-2">
            {cuj.steps.map((step) => (
              <li
                key={step.order}
                className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300"
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                  {step.order}
                </span>
                <div>
                  <span>{step.action}</span>
                  {step.route && (
                    <code className="ml-1 rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                      {step.method ?? "GET"} {step.route}
                    </code>
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
