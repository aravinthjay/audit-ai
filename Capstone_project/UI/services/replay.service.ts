import { apiRequest } from "@/services/api";
import type { ReplayFrame, WorkState } from "@/types/domain";

type ApiReplayFrame = {
  id: string;
  title: string;
  agent: string;
  timestamp?: string | null;
  state: string;
  prompt: string;
  input: string;
  output: string;
  citations?: string[] | null;
  token_usage?: number | null;
  cost?: number | null;
};

export async function getReplayFrames(caseId?: string): Promise<ReplayFrame[]> {
  if (!caseId) {
    return [];
  }

  const rows = await apiRequest<ApiReplayFrame[]>(`/investigations/${caseId}/replay`);

  return rows.map((row) => ({
    id: row.id,
    title: row.title,
    agent: row.agent,
    timestamp: row.timestamp ?? "",
    state: row.state as WorkState,
    prompt: row.prompt,
    input: row.input,
    output: row.output,
    citations: row.citations ?? [],
    tokenUsage: row.token_usage ?? 0,
    cost: row.cost ?? 0,
  }));
}
