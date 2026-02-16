import { Link } from "react-router-dom";
import type { FeatureArea } from "../../types";

const methodColors: Record<string, string> = {
  create: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  read: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  update: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  delete: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

interface FeatureCardProps {
  feature: FeatureArea;
}

export function FeatureCard({ feature }: FeatureCardProps) {
  return (
    <Link
      to={`/doc/features/${feature.id}`}
      className="block rounded-lg border border-slate-200 bg-white p-5 transition hover:border-slate-300 hover:shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
    >
      <div className="flex items-start justify-between">
        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          {feature.name}
        </h3>
        {feature.auth_required && (
          <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
            Auth
          </span>
        )}
      </div>

      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {feature.routes.length} route{feature.routes.length !== 1 ? "s" : ""}
      </p>

      {feature.crud_operations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {feature.crud_operations.map((op) => (
            <span
              key={op}
              className={`rounded px-2 py-0.5 text-xs font-medium ${methodColors[op] ?? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}
            >
              {op.toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {feature.description && (
        <p className="mt-2 line-clamp-2 text-xs text-slate-400 dark:text-slate-500">
          {feature.description}
        </p>
      )}
    </Link>
  );
}
