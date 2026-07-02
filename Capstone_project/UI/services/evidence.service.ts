import { apiRequest } from "@/services/api";
import { normalizeProviderName, normalizeVerificationReason } from "@/services/evidence-verification.service";
import type { EvidenceSource, EvidenceVerification } from "@/types/domain";

type ApiEvidence = {
  id: string;
  source: string;
  content: string;
  citations?: unknown[] | null;
  relevance_score?: number | null;
  created_at: string;
};

function evidenceType(source: string): EvidenceSource["type"] {
  const normalized = source.toLowerCase();

  if (normalized.includes("policy")) {
    return "Policy";
  }
  if (normalized.includes("vendor")) {
    return "Vendor";
  }
  if (normalized.includes("history") || normalized.includes("analytics")) {
    return "History";
  }
  if (normalized.includes("contract") || normalized.includes("sow")) {
    return "Contract";
  }
  if (normalized.includes("api") || normalized.includes("registry")) {
    return "External API";
  }

  return "Ledger";
}

function quality(score: number): EvidenceSource["quality"] {
  if (score >= 0.8) {
    return "strong";
  }
  if (score >= 0.55) {
    return "adequate";
  }
  if (score > 0) {
    return "weak";
  }

  return "missing";
}

function citationFor(row: ApiEvidence) {
  const first = row.citations?.[0];

  if (typeof first === "string" && first.trim()) {
    return first;
  }

  return row.source;
}

function mapEvidence(row: ApiEvidence, caseId: string): EvidenceSource {
  const confidence = row.relevance_score ?? 0;

  return {
    id: row.id,
    title: row.source,
    type: evidenceType(row.source),
    citation: citationFor(row),
    summary: row.content,
    version: "api",
    confidence,
    owner: "Evidence agent",
    lastVerified: row.created_at,
    linkedCases: [caseId],
    tags: [row.source],
    quality: quality(confidence),
    preview: row.content,
  };
}

function formatAmount(value?: number | null) {
  if (typeof value !== "number") {
    return "unavailable";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value?: number | null) {
  if (typeof value !== "number") {
    return "unavailable";
  }

  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

function verificationQuality(verification: EvidenceVerification): EvidenceSource["quality"] {
  if (verification.verificationStatus === "VERIFIED") {
    return "strong";
  }
  if (verification.verificationStatus === "FLAGGED") {
    return "weak";
  }
  if (verification.verificationStatus === "API_UNAVAILABLE") {
    return "missing";
  }

  return "adequate";
}

export function evidenceFromVerification(
  verification: EvidenceVerification | null | undefined,
  caseId: string,
): EvidenceSource | null {
  if (!verification) {
    return null;
  }

  const providerName = normalizeProviderName(verification.providerName);
  const reason = normalizeVerificationReason(verification.reason);
  const range =
    typeof verification.minAcceptableAmount === "number" &&
    typeof verification.maxAcceptableAmount === "number"
      ? `${formatAmount(verification.minAcceptableAmount)} to ${formatAmount(verification.maxAcceptableAmount)}`
      : "unavailable";
  const summary = [
    `Third-party status ${verification.verificationStatus}.`,
    `Claimed ${formatAmount(verification.claimedAmount)}; provider reference ${formatAmount(verification.fetchedAmount)}.`,
    `Difference ${formatAmount(verification.differenceAmount)} (${formatPercent(verification.differencePercentage)}).`,
    `Allowed range ${range}.`,
  ].join(" ");

  return {
    id: verification.id ? `third-party-${verification.id}` : `third-party-${caseId}`,
    title: "third_party_evidence_verification",
    type: "External API",
    citation: verification.providerReferenceId || providerName,
    summary,
    version: "api",
    confidence: verification.confidenceScore,
    owner: providerName,
    lastVerified: verification.updatedAt,
    linkedCases: [caseId],
    tags: [
      "third_party_api",
      verification.category,
      verification.verificationStatus.toLowerCase(),
    ],
    quality: verificationQuality(verification),
    preview: reason,
  };
}

export async function getEvidence(caseId?: string): Promise<EvidenceSource[]> {
  if (!caseId) {
    return [];
  }

  const rows = await apiRequest<ApiEvidence[]>(`/investigations/${caseId}/evidence`);
  return rows.map((row) => mapEvidence(row, caseId));
}
