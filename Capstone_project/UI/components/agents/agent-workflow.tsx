"use client";

import "reactflow/dist/style.css";

import ReactFlow, {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import { useMemo } from "react";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { StatusBadge } from "@/components/shared/status-badge";
import { cn } from "@/lib/utils";
import type { PipelineStep } from "@/types/domain";

type WorkflowNodeData = {
  step: PipelineStep;
};

function WorkflowNode({ data }: NodeProps<WorkflowNodeData>) {
  return (
    <div className="w-64 rounded-lg border border-border bg-card p-3 shadow-card">
      <Handle type="target" position={Position.Left} className="!bg-primary" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{data.step.role}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{data.step.detail}</p>
        </div>
        <StatusBadge state={data.step.state} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 rounded-md border border-border bg-muted/40 p-2 text-[11px] text-muted-foreground">
        <span>
          Latency <span className="font-mono text-foreground">{data.step.latency ?? "n/a"}</span>
        </span>
        <span>
          Attempt <span className="font-mono text-foreground">{data.step.attempt}</span>
        </span>
        <span>
          Tokens <span className="font-mono text-foreground">{data.step.tokenUsage}</span>
        </span>
        <span>
          Cost <span className="font-mono text-foreground">${data.step.cost.toFixed(2)}</span>
        </span>
      </div>
      {typeof data.step.confidence === "number" ? (
        <ConfidenceMeter value={data.step.confidence} className="mt-3" />
      ) : null}
      <details className="mt-3 text-xs text-muted-foreground">
        <summary className="cursor-pointer text-primary">Expand details</summary>
        <p className="mt-2 leading-5">{data.step.expandedDetail}</p>
      </details>
      <Handle type="source" position={Position.Right} className="!bg-primary" />
    </div>
  );
}

const nodeTypes = {
  workflow: WorkflowNode,
};

export function AgentWorkflow({ steps, className }: { steps: PipelineStep[]; className?: string }) {
  const nodes = useMemo<Node<WorkflowNodeData>[]>(
    () =>
      steps.map((step, index) => ({
        id: step.id,
        type: "workflow",
        position: {
          x: (index % 4) * 310,
          y: Math.floor(index / 4) * 190,
        },
        data: { step },
      })),
    [steps],
  );

  const edges = useMemo<Edge[]>(
    () =>
      steps.slice(1).map((step, index) => ({
        id: `${steps[index].id}-${step.id}`,
        source: steps[index].id,
        target: step.id,
        animated: step.state === "running" || step.state === "queued",
        style: { stroke: "hsl(var(--primary))" },
      })),
    [steps],
  );

  return (
    <div className={cn("h-[520px] overflow-hidden rounded-lg border border-border bg-card", className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.55}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        onlyRenderVisibleElements
      >
        <Background color="hsl(var(--border))" gap={20} />
        <MiniMap pannable zoomable className="!bg-muted" />
        <Controls className="!border-border !bg-card !text-foreground" />
      </ReactFlow>
    </div>
  );
}
