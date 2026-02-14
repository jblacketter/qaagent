import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
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
import type { ArchitectureNode, ArchitectureEdge } from "../../types";

const nodeTypes = { feature: FeatureNode };

interface FeatureMapDiagramProps {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export function FeatureMapDiagram({ nodes: rawNodes, edges: rawEdges }: FeatureMapDiagramProps) {
  const navigate = useNavigate();

  const initialNodes = useMemo(
    () =>
      rawNodes.map((n) => ({
        id: n.id,
        type: "feature",
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
        animated: e.type.includes("shared_integration"),
      })),
    [rawEdges]
  );

  const [flowNodes, , onNodesChange] = useNodesState(initialNodes);
  const [flowEdges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string }) => {
      const featureId = node.id.replace("feat-", "");
      navigate(`/doc/features/${featureId}`);
    },
    [navigate]
  );

  return (
    <div className="h-[500px] w-full rounded-lg border border-slate-200 dark:border-slate-700">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
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
