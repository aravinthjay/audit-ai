import { ApiError, apiRequest } from "@/services/api";
import type { EvidenceVerification } from "@/types/domain";

type ApiEvidenceVerification = {
  id?: string | null;
  claim_id?: string | null;
  category: string;
  claimed_amount: number;
  fetched_amount?: number | null;
  min_acceptable_amount?: number | null;
  max_acceptable_amount?: number | null;
  difference_amount?: number | null;
  difference_percentage?: number | null;
  tolerance_percentage: number;
  provider_name: string;
  provider_reference_id?: string | null;
  verification_status: EvidenceVerification["verificationStatus"];
  confidence_score: number;
  reason: string;
  created_at: string;
  updated_at: string;
};

export type EvidenceVerificationRequest = {
  category?: string;
  claimedAmount?: number;
  vendor?: string;
  gstin?: string;
  routeFrom?: string;
  routeTo?: string;
  serviceDate?: string;
  invoiceDate?: string;
  quantity?: number;
  currency?: string;
  location?: string;
  metadata?: Record<string, unknown>;
};

function mapEvidenceVerification(row: ApiEvidenceVerification): EvidenceVerification {
  return {
    id: row.id ?? undefined,
    claimId: row.claim_id ?? undefined,
    category: row.category,
    claimedAmount: row.claimed_amount,
    fetchedAmount: row.fetched_amount ?? null,
    minAcceptableAmount: row.min_acceptable_amount ?? null,
    maxAcceptableAmount: row.max_acceptable_amount ?? null,
    differenceAmount: row.difference_amount ?? null,
    differencePercentage: row.difference_percentage ?? null,
    tolerancePercentage: row.tolerance_percentage,
    providerName: normalizeProviderName(row.provider_name),
    providerReferenceId: row.provider_reference_id ?? null,
    verificationStatus: row.verification_status,
    confidenceScore: row.confidence_score,
    reason: normalizeVerificationReason(row.reason),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function normalizeProviderName(value: string) {
  return value;
}

export function normalizeVerificationReason(value: string) {
  if (!value.includes("No reliable third-party benchmark provider")) {
    return value;
  }

  return value.replace(
    "No reliable third-party benchmark provider is configured for this claim category; reviewer assessment is required.",
    "No real-time third-party provider response is available for this claim category; reviewer assessment is required.",
  );
}

function toApiPayload(input?: EvidenceVerificationRequest) {
  if (!input) {
    return undefined;
  }

  return {
    category: input.category,
    claimed_amount: input.claimedAmount,
    vendor: input.vendor,
    gstin: input.gstin,
    route_from: input.routeFrom,
    route_to: input.routeTo,
    service_date: input.serviceDate,
    invoice_date: input.invoiceDate,
    quantity: input.quantity,
    currency: input.currency,
    location: input.location,
    metadata: input.metadata,
  };
}

export async function getEvidenceVerification(caseId?: string): Promise<EvidenceVerification | null> {
  if (!caseId) {
    return null;
  }

  try {
    const row = await apiRequest<ApiEvidenceVerification>(`/claims/${caseId}/verification`);
    return mapEvidenceVerification(row);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function verifyEvidence(
  caseId: string,
  input?: EvidenceVerificationRequest,
): Promise<EvidenceVerification> {
  const payload = toApiPayload(input);
  const row = await apiRequest<ApiEvidenceVerification>(`/claims/${caseId}/verify-evidence`, {
    method: "POST",
    body: payload ? JSON.stringify(payload) : undefined,
  });

  return mapEvidenceVerification(row);
}

export async function verifyEvidencePreview(
  input: EvidenceVerificationRequest & { category: string; claimedAmount: number },
): Promise<EvidenceVerification> {
  const row = await apiRequest<ApiEvidenceVerification>("/claims/verify-preview", {
    method: "POST",
    body: JSON.stringify(toApiPayload(input)),
  });

  return mapEvidenceVerification(row);
}
