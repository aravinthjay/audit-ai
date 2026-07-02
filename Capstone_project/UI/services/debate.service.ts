import { apiRequest } from "@/services/api";
import type { DebateArgument } from "@/types/domain";

type ApiDebateMessage = {
  id: string;
  round: number;
  speaker: string;
  message: string;
  token_count?: number | null;
  confidence?: number | null;
  created_at: string;
};

function sideFor(speaker: string): DebateArgument["side"] {
  const normalized = speaker.toLowerCase();

  if (normalized.includes("defender")) {
    return "defender";
  }
  if (normalized.includes("adjudicator")) {
    return "adjudicator";
  }

  return "challenger";
}

function mapDebateMessage(row: ApiDebateMessage): DebateArgument {
  const side = sideFor(row.speaker);
  const label = side.charAt(0).toUpperCase() + side.slice(1);

  return {
    id: row.id,
    side,
    title: `${label} round ${row.round}`,
    timestamp: row.created_at,
    summary: row.message,
    tags: [label, `Round ${row.round}`],
    footer: `${row.token_count ?? 0} tokens recorded`,
    scoreLabel: `Round ${row.round}`,
    citations: [],
    confidence: typeof row.confidence === "number" ? row.confidence : undefined,
    details: row.message,
  };
}

export async function getDebateArguments(caseId?: string): Promise<DebateArgument[]> {
  if (!caseId) {
    return [];
  }

  const rows = await apiRequest<ApiDebateMessage[]>(`/investigations/${caseId}/debate`);
  return rows.map(mapDebateMessage);
}
