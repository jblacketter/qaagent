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

import { FeatureNode } from "./nodes/FeatureNode";
import { IntegrationNode } from "./nodes/IntegrationNode";
import type { ArchitectureNode, ArchitectureEdge } from "../../types";

const nodeTypes = {
  feature: FeatureNode,
  integration: IntegrationNode,
};

interface IntegrationMapDiagramProps {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export function IntegrationMapDiagram({ nodes: rawNodes, edges: rawEdges }: IntegrationMapDiagramProps) {
  const initialNodes = useMemo(
    () =>
      rawNodes.map((n) => ({
        id: n.id,
        type: n.type as "feature" | "integration",
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
        label: e.label ?? undefined,
        animated: true,
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
