import { apiRequest } from "@/services/api";
import type { AgentHealth, PipelineStep, WorkState } from "@/types/domain";

type ApiAgentHealth = {
  label: AgentHealth["label"];
  state: WorkState;
  latency: string;
  load: number;
};

type ApiPipelineStep = {
  id: string;
  role: PipelineStep["role"];
  state: WorkState;
  detail: string;
  latency?: string | null;
  confidence?: number | null;
  token_usage?: number | null;
  cost?: number | null;
  attempt?: number | null;
  expanded_detail: string;
};

function mapPipelineStep(step: ApiPipelineStep): PipelineStep {
  return {
    id: step.id,
    role: step.role,
    state: step.state,
    detail: step.detail,
    latency: step.latency ?? undefined,
    confidence: step.confidence ?? undefined,
    tokenUsage: step.token_usage ?? 0,
    cost: step.cost ?? 0,
    attempt: step.attempt ?? 1,
    expandedDetail: step.expanded_detail,
  };
}

export async function getAgentHealth(): Promise<AgentHealth[]> {
  return apiRequest<ApiAgentHealth[]>("/agents/health");
}

export async function getAgentWorkflow(caseId?: string): Promise<PipelineStep[]> {
  if (!caseId) {
    return [];
  }

  const steps = await apiRequest<ApiPipelineStep[]>(`/agents/workflow/${encodeURIComponent(caseId)}`);
  return steps.map(mapPipelineStep);
}
