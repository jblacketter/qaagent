import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";

interface FeatureNodeData {
  label: string;
  route_count?: number;
  crud_operations?: string[];
  auth_required?: boolean;
  [key: string]: unknown;
}

function FeatureNodeComponent({ data }: NodeProps) {
  const nodeData = data as FeatureNodeData;

  return (
    <div className="rounded-lg border-2 border-blue-300 bg-white px-4 py-3 shadow-sm dark:border-blue-600 dark:bg-slate-800">
      <Handle type="target" position={Position.Left} className="!bg-blue-500" />
      <Handle type="source" position={Position.Right} className="!bg-blue-500" />

      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-blue-500" />
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {nodeData.label}
        </span>
      </div>

      <div className="mt-1 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        {nodeData.route_count !== undefined && (
          <span>{nodeData.route_count} routes</span>
        )}
        {nodeData.auth_required && (
          <span className="rounded bg-purple-100 px-1 py-0.5 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
            Auth
          </span>
        )}
      </div>

      {nodeData.crud_operations && nodeData.crud_operations.length > 0 && (
        <div className="mt-1 flex gap-1">
          {nodeData.crud_operations.map((op: string) => (
            <span
              key={op}
              className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-500 dark:bg-slate-700 dark:text-slate-400"
            >
              {op[0].toUpperCase()}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export const FeatureNode = memo(FeatureNodeComponent);
