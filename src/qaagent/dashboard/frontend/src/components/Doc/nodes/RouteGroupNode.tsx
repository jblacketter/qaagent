import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";

interface RouteGroupNodeData {
  label: string;
  route_count?: number;
  depth?: number;
  [key: string]: unknown;
}

function RouteGroupNodeComponent({ data }: NodeProps) {
  const nodeData = data as RouteGroupNodeData;

  return (
    <div className="rounded-lg border-2 border-amber-300 bg-white px-4 py-2 shadow-sm dark:border-amber-600 dark:bg-slate-800">
      <Handle type="target" position={Position.Left} className="!bg-amber-500" />
      <Handle type="source" position={Position.Right} className="!bg-amber-500" />

      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
          {nodeData.label}
        </span>
      </div>

      {nodeData.route_count !== undefined && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {nodeData.route_count} route{nodeData.route_count !== 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
}

export const RouteGroupNode = memo(RouteGroupNodeComponent);
