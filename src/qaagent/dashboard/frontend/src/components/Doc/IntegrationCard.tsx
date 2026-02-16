import type { Integration } from "../../types";

const typeColors: Record<string, string> = {
  http_client: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  sdk: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  database: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  message_queue: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  storage: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
  auth_provider: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  webhook: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300",
  unknown: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

interface IntegrationCardProps {
  integration: Integration;
}

export function IntegrationCard({ integration }: IntegrationCardProps) {
  const colorClass = typeColors[integration.type] ?? typeColors.unknown;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between">
        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          {integration.name}
        </h3>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
          {integration.type.replace("_", " ")}
        </span>
      </div>

      {integration.package && (
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          <code className="rounded bg-slate-100 px-1 py-0.5 text-xs dark:bg-slate-800">
            {integration.package}
          </code>
        </p>
      )}

      {integration.env_vars.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Environment Variables
          </p>
          <div className="mt-1 flex flex-wrap gap-1">
            {integration.env_vars.map((v) => (
              <code
                key={v}
                className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              >
                {v}
              </code>
            ))}
          </div>
        </div>
      )}

      {integration.connected_features.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Connected Features
          </p>
          <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
            {integration.connected_features.join(", ")}
          </p>
        </div>
      )}

      {integration.description && (
        <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
          {integration.description}
        </p>
      )}
    </div>
  );
}
