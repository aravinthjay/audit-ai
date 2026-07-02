import { apiRequest } from "@/services/api";
import { normalizeProviderName, normalizeVerificationReason } from "@/services/evidence-verification.service";
import type { AuditEvent, WorkState } from "@/types/domain";

export type ApiAuditEvent = {
  id: string;
  type: string;
  data: {
    event_type?: string;
    investigation_id?: string;
    actor?: string;
    details?: Record<string, unknown>;
    timestamp?: string;
  };
  hash?: string | null;
  sequence?: number | null;
};

function titleFor(type: string) {
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function stateFor(type: string): WorkState {
  if (type.includes("rejected") || type.includes("failed")) {
    return "failed";
  }
  if (type.includes("escalated") || type.includes("review") || type.includes("evidence_requested")) {
    return "review";
  }
  if (type.includes("created") || type.includes("started")) {
    return "running";
  }

  return "done";
}

function eventKind(type: string): AuditEvent["eventType"] {
  if (type.includes("approved") || type.includes("rejected") || type.includes("evidence_requested") || type.includes("escalated")) {
    return "human";
  }
  if (type.includes("evidence")) {
    return "source";
  }
  if (type.includes("case_")) {
    return "system";
  }

  return "agent";
}

function money(value: unknown) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(value)
    : "unavailable";
}

function pct(value: unknown) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-US", {
        style: "percent",
        maximumFractionDigits: 1,
      }).format(value)
    : "unavailable";
}

function verificationDetailFor(details: Record<string, unknown>) {
  const provider =
    typeof details.provider_name === "string"
      ? normalizeProviderName(details.provider_name)
      : "third_party_provider";
  const status =
    typeof details.verification_status === "string"
      ? details.verification_status.replaceAll("_", " ").toLowerCase()
      : "recorded";
  const reason =
    typeof details.reason === "string"
      ? normalizeVerificationReason(details.reason)
      : "No provider reason was recorded.";

  return [
    `Third-party verification ${status}.`,
    `Provider: ${provider}.`,
    `Claimed ${money(details.claimed_amount)}; reference ${money(details.fetched_amount)}.`,
    `Difference ${money(details.difference_amount)} (${pct(details.difference_percentage)}).`,
    reason,
  ].join(" ");
}

function detailFor(type: string, details?: Record<string, unknown>) {
  if (!details || Object.keys(details).length === 0) {
    return "No additional details were recorded.";
  }

  if (typeof details.comment === "string" && details.comment.trim()) {
    return details.comment;
  }

  if (type === "verification_completed" && "verification_id" in details) {
    return verificationDetailFor(details);
  }

  return JSON.stringify(details);
}

export function mapAuditEvent(row: ApiAuditEvent, fallbackCaseId: string): AuditEvent {
  const type = row.data.event_type ?? row.type;
  const caseId = row.data.investigation_id ?? fallbackCaseId;

  return {
    id: row.id,
    caseId,
    title: titleFor(type),
    detail: detailFor(type, row.data.details),
    timestamp: row.data.timestamp ?? "",
    state: stateFor(type),
    actor: row.data.actor ?? "system",
    hash: row.hash ? `sha256:${row.hash.slice(0, 8)}` : `sequence:${row.sequence ?? 0}`,
    eventType: eventKind(type),
    sourceRef: `${type}/${caseId}`,
  };
}

export async function getAuditEvents(caseId?: string): Promise<AuditEvent[]> {
  // Case-scoped when a case is selected; otherwise fall back to the most recent
  // events across every investigation so the global audit log is never empty.
  const path = caseId ? `/investigations/${caseId}/audit` : "/audit/recent";
  const rows = await apiRequest<ApiAuditEvent[]>(path);
  return rows.map((row) => mapAuditEvent(row, caseId ?? ""));
}
