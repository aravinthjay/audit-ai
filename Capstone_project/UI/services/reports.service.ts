import { apiRequest } from "@/services/api";
import type { ReportArtifact, RiskLevel } from "@/types/domain";

type ApiReport = {
  id: string;
  title: string;
  status: ReportArtifact["status"];
  updated_at?: string | null;
  confidence: number;
  audience: ReportArtifact["audience"];
  risk_verdict: string;
  sections: string[];
  executive_summary: string;
  human_decision: string;
  reviewer_signature: string;
};

const riskLevels: RiskLevel[] = ["critical", "high", "medium", "low", "cleared"];

function asRisk(value: string): RiskLevel {
  return (riskLevels as string[]).includes(value) ? (value as RiskLevel) : "medium";
}

function formatDate(value?: string | null) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value.slice(0, 10) : date.toISOString().slice(0, 10);
}

export async function getReports(): Promise<ReportArtifact[]> {
  const rows = await apiRequest<ApiReport[]>("/reports");

  return rows.map((row) => ({
    id: row.id,
    title: row.title,
    status: row.status,
    updatedAt: formatDate(row.updated_at),
    confidence: row.confidence,
    audience: row.audience,
    sections: row.sections,
    riskVerdict: asRisk(row.risk_verdict),
    executiveSummary: row.executive_summary,
    humanDecision: row.human_decision,
    reviewerSignature: row.reviewer_signature,
  }));
}
