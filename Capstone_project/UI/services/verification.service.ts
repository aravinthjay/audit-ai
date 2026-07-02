import { apiRequest } from "@/services/api";
import type { VerificationClaim } from "@/types/domain";

type ApiVerificationClaim = {
  id: string;
  claim_text: string;
  is_grounded?: boolean | null;
  explanation?: string | null;
  supporting_evidence?: unknown[] | null;
  created_at: string;
};

function supportingEvidence(value?: unknown[] | null) {
  if (!value?.length) {
    return "No supporting evidence attached.";
  }

  return value
    .map((item) => (typeof item === "string" ? item : JSON.stringify(item)))
    .join(", ");
}

function mapVerificationClaim(row: ApiVerificationClaim): VerificationClaim {
  const grounded = Boolean(row.is_grounded);

  return {
    id: row.id,
    claim: row.claim_text,
    citation: "Backend verification record",
    status: grounded ? "grounded" : "unsupported",
    confidence: grounded ? 0.9 : 0.45,
    owner: "Verifier",
    supportingEvidence: supportingEvidence(row.supporting_evidence),
    notes: row.explanation ?? "Verification completed without additional notes.",
    pass: grounded ? "first_pass" : "failed",
    action: grounded ? "proceed" : "revise",
  };
}

export async function getVerificationClaims(caseId?: string): Promise<VerificationClaim[]> {
  if (!caseId) {
    return [];
  }

  const rows = await apiRequest<ApiVerificationClaim[]>(`/investigations/${caseId}/verification`);
  return rows.map(mapVerificationClaim);
}
