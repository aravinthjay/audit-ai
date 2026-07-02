import { apiRequest } from "@/services/api";
import type { ApiAuditEvent } from "@/services/audit.service";
import type { ReviewHistoryItem } from "@/types/domain";

export type ReviewDecision = "approve" | "reject" | "request_evidence" | "escalate";

export type SubmitReviewDecisionInput = {
  caseId: string;
  decision: ReviewDecision;
  comment: string;
  signature: string;
};

type ReviewActionResponse = {
  investigation_id: string;
  action: ReviewDecision;
  status: string;
  message: string;
};

const reviewEventActions: Record<string, ReviewHistoryItem["action"]> = {
  case_approved: "approved",
  case_rejected: "rejected",
  case_evidence_requested: "requested_evidence",
  case_escalated: "escalated",
};

function mapHistory(row: ApiAuditEvent): ReviewHistoryItem | null {
  const type = row.data.event_type ?? row.type;
  const action = reviewEventActions[type];

  if (!action) {
    return null;
  }

  const comment = row.data.details?.comment;

  return {
    id: row.id,
    actor: row.data.actor ?? "system",
    action,
    comment: typeof comment === "string" && comment.trim() ? comment : "Review action recorded.",
    timestamp: row.data.timestamp ?? "",
    signature: row.data.actor ?? "system",
  };
}

export async function getReviewHistory(caseId?: string): Promise<ReviewHistoryItem[]> {
  if (!caseId) {
    return [];
  }

  const rows = await apiRequest<ApiAuditEvent[]>(`/investigations/${caseId}/audit`);
  return rows.map(mapHistory).filter((item): item is ReviewHistoryItem => item !== null);
}

export async function submitReviewDecision(input: SubmitReviewDecisionInput): Promise<ReviewActionResponse> {
  const endpoint = input.decision === "request_evidence" ? "request-evidence" : input.decision;

  return apiRequest<ReviewActionResponse>(`/reviews/${input.caseId}/${endpoint}`, {
    method: "POST",
    body: JSON.stringify({
      actor: input.signature,
      comment: input.comment,
    }),
  });
}
