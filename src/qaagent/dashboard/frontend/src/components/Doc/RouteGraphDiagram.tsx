import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { RouteGroupNode } from "./nodes/RouteGroupNode";
import type { ArchitectureNode, ArchitectureEdge } from "../../types";

const nodeTypes = { route_group: RouteGroupNode };

interface RouteGraphDiagramProps {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export function RouteGraphDiagram({ nodes: rawNodes, edges: rawEdges }: RouteGraphDiagramProps) {
  const initialNodes = useMemo(
    () =>
      rawNodes.map((n) => ({
        id: n.id,
        type: "route_group",
        position: n.position ?? { x: 0, y: 0 },
        data: { label: n.label, ...n.metadata },
      })),
    [rawNodes]
  );

  const initialEdges = useMemo(
    () =>
      rawEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      })),
    [rawEdges]
  );

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(initialNodes);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => { setFlowNodes(initialNodes); }, [initialNodes, setFlowNodes]);
  useEffect(() => { setFlowEdges(initialEdges); }, [initialEdges, setFlowEdges]);

  return (
    <div className="h-[500px] w-full rounded-lg border border-slate-200 dark:border-slate-700">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
