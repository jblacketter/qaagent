import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";

interface IntegrationNodeData {
  label: string;
  integration_type?: string;
  env_vars?: string[];
  package?: string | null;
  [key: string]: unknown;
}

const typeColors: Record<string, string> = {
  http_client: "border-blue-400 dark:border-blue-500",
  sdk: "border-indigo-400 dark:border-indigo-500",
  database: "border-emerald-400 dark:border-emerald-500",
  message_queue: "border-orange-400 dark:border-orange-500",
  storage: "border-cyan-400 dark:border-cyan-500",
  auth_provider: "border-purple-400 dark:border-purple-500",
  webhook: "border-pink-400 dark:border-pink-500",
};

function IntegrationNodeComponent({ data }: NodeProps) {
  const nodeData = data as IntegrationNodeData;
  const borderColor = typeColors[nodeData.integration_type ?? ""] ?? "border-slate-300 dark:border-slate-600";

  return (
    <div className={`rounded-lg border-2 ${borderColor} bg-white px-4 py-3 shadow-sm dark:bg-slate-800`}>
      <Handle type="target" position={Position.Left} className="!bg-emerald-500" />
      <Handle type="source" position={Position.Right} className="!bg-emerald-500" />

      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-emerald-500" />
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {nodeData.label}
        </span>
      </div>

      {nodeData.integration_type && (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          {nodeData.integration_type.replace("_", " ")}
        </p>
      )}

      {nodeData.env_vars && nodeData.env_vars.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {nodeData.env_vars.slice(0, 2).map((v: string) => (
            <code
              key={v}
              className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-500 dark:bg-slate-700 dark:text-slate-400"
            >
              {v}
            </code>
          ))}
          {nodeData.env_vars.length > 2 && (
            <span className="text-xs text-slate-400">+{nodeData.env_vars.length - 2}</span>
          )}
        </div>
      )}
    </div>
  );
}

export const IntegrationNode = memo(IntegrationNodeComponent);
